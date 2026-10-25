import ctypes
import math
import random
import time
from ctypes import wintypes

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QGuiApplication, QPainter
from PySide6.QtWidgets import QWidget

from lct.sprites import load_character

ACCEL = 40.0  # px/s^2, so starts, stops and turns look gradual
MIN_SPEED, MAX_SPEED = 14.0, 30.0  # a calm stroll; the pace only drifts a little between phases
TAKEOFF_SPEED = 18.0  # flying characters are fully airborne from this speed
AWAY_SPEED = 120.0  # brisk walk off screen when a fullscreen app takes over

PET_CHAIN = 1.0  # clicks closer together than this (seconds) count as one run of petting
PET_REST = 1.6  # the character stays put this long after the last click
OVERWHELM_AT = 8  # clicks in one run before it has had enough
# The "too much love" dash: a run of about a seventh of the screen, at a speed that scales with the
# character so that small and large ones both look like they are really bolting.
SPRINT_ACCEL, SPRINT_BRAKE = 700.0, 400.0
SPRINT_BODY_LENGTHS_PER_SECOND, SPRINT_MIN_SPEED = 4.5, 200.0
SPRINT_SCREEN_SHARE, SPRINT_MIN_DISTANCE, SPRINT_MAX_DISTANCE = 0.15, 175.0, 350.0

HOVER_MOVE_WINDOW = 0.25  # the pointer must have been moved this recently to "grab" the character
HOVER_RELEASE_AFTER = 0.15  # and it must stay off the character this long before it is let go

GWL_EXSTYLE, WS_EX_TRANSPARENT = -20, 0x20
_user32 = getattr(ctypes, "windll", None) and ctypes.windll.user32
if _user32:
    _user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    _user32.GetWindowLongW.restype = ctypes.c_long
    _user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    _user32.SetWindowLongW.restype = ctypes.c_long
    _user32.GetAsyncKeyState.argtypes = [ctypes.c_int]


def _mouse_button_down():
    """The real state of the mouse buttons, straight from Windows.

    Not Qt's QGuiApplication.mouseButtons(): that is only the state at the last mouse event Qt saw.
    The character window ignores the mouse almost all of the time, and a click that Windows handles by
    itself (the minimize button of another window of ours) can leave Qt's copy stuck on 'pressed'.
    With nothing delivering new mouse events, it then stayed stuck, and the character treated every
    visit of the pointer as a drag started in another app and never took the mouse."""
    if not _user32:
        return QGuiApplication.mouseButtons() != Qt.NoButton
    return any(_user32.GetAsyncKeyState(vk) & 0x8000 for vk in (0x01, 0x02, 0x04))  # left, right, middle


class Mascot(QWidget):
    """A frameless sprite that strolls along the taskbar and can be petted with a click.

    The window lets mouse input fall straight through (WS_EX_TRANSPARENT) except while the
    pointer is over one of the character's visible pixels. A window that takes mouse events makes
    Windows re-evaluate the cursor whenever it moves under the pointer, which showed up as the
    cursor flickering while typing near the bottom of the screen; this way it only happens when
    you really point at the character. A mouse drag that started in another app never counts.
    """

    moved = Signal(QPoint)  # global position of the top centre of the sprite
    hearts = Signal(int, QPoint)  # how many hearts to release, and the point on top of the sprite

    def __init__(self, char_id, scale):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                         | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setCursor(Qt.PointingHandCursor)
        self.clickable = True  # off: the window never takes the mouse at all
        self._click_through = None  # unknown until the native window exists
        self._pressing = False
        self._grabbed = False  # the pointer was moved onto the character and the window takes the mouse
        self._pointer = None
        self._pointer_moved_at = 0.0
        self._off_since = None
        self._hover_until = 0.0
        self._streak = 0
        self._last_click = 0.0
        self._petted_until = 0.0
        self._sprint_left = 0.0
        self._hit_cache = {}
        self.char = None
        self._shown_state = None  # what was last painted, to skip identical repaints
        self._pos = None  # last window position handed to the system
        self.hold = False  # stand still, e.g. while a bubble is open
        self._away = False  # walking off screen (or already gone) because a fullscreen app is up
        self._gone = False  # fully off screen, window hidden
        self._entering = False  # walking back in from beyond the screen edge
        self._frame = 0
        self._facing = 1
        self._dir = random.choice((-1, 1))
        self._x = 0.0
        self._speed = 0.0
        self._target = 0.0
        self._walking = False
        self._phase_left = 0.0
        self._frame_clock = 0.0
        self._fidget_left = 0
        self._next_fidget = random.uniform(2, 6)
        self._t0 = time.perf_counter()
        self._last = self._t0
        self.set_character(char_id, scale)
        ag = self._area()
        self._x = random.uniform(ag.left(), ag.right() - self.width())
        self._begin_phase()

        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        # 16 ms, not 33: at a calm 20 px/s the sprite advances one pixel every 50 ms, and a 33 ms tick
        # makes those pixel steps alternate between 33 and 66 ms, which shows up as judder.
        # The window is still only moved or repainted when something actually changed.
        self._timer.start(16)

    def set_character(self, char_id, scale):
        self.char = load_character(char_id, scale)
        self._scale = scale
        w = max(p.width() for p in self.char.frames)
        h = max(p.height() for p in self.char.frames)
        self._pad = (self.char.hover + self.char.bob) * scale  # head room for flying characters
        self.setFixedSize(w, h + self._pad)
        self._frame = self.char.idle_frame
        self._step = 0
        self._hit_cache.clear()
        self._pos = None  # force a move and an anchor update for the new size
        self._shown_state = None
        self._place()
        self.update()

    def _area(self):
        screen = QGuiApplication.primaryScreen()
        return screen.availableGeometry()

    def _ground_y(self):
        return self._area().bottom() + 1 - self.height()

    def _bounds(self):
        ag = self._area()
        left, right = ag.left(), ag.right() + 1 - self.width()
        if self._away or self._entering:  # free to cross the screen edge
            return left - self.width() - 4, right + self.width() + 4
        return left, right

    def set_away(self, away):
        """Walk off the nearest screen edge and hide, or walk back in from a random side."""
        if away == self._away:
            return
        self._away = away
        ag = self._area()
        if away:
            self.hold = False
            self._entering = False
            centre = self._x + self.width() / 2
            self._dir = -1 if centre < (ag.left() + ag.right()) / 2 else 1
            self._walking, self._target, self._phase_left = True, AWAY_SPEED, 1e9
            return
        self._entering = True
        self._walking, self._phase_left = True, random.uniform(6.0, 10.0)
        self._target = random.uniform(MIN_SPEED, MAX_SPEED)
        if not self._gone:  # still on its way out: just turn back towards the middle
            centre = self._x + self.width() / 2
            self._dir = 1 if centre < (ag.left() + ag.right()) / 2 else -1
            return
        side = random.choice((-1, 1))  # which edge it comes in from
        self._x = ag.left() - self.width() if side < 0 else ag.right() + 1
        self._dir = -side
        self._speed = 0.0
        self._gone = False
        self._pos = None
        self._place()
        self.show()

    def _place(self):
        lo, hi = self._bounds()
        self._x = min(max(self._x, lo), hi)
        pos = (round(self._x), self._ground_y())
        if pos != self._pos:  # touching the window when nothing changed only causes flicker
            self._pos = pos
            self.move(*pos)
            self.moved.emit(QPoint(pos[0] + self.width() // 2, pos[1] + self._pad))

    def _lift(self):
        """Pixels the sprite is raised off the ground: hovering and bobbing for flyers."""
        c = self.char
        if not (c.floating or c.flying):
            return 0
        airborne = 1.0 if c.floating else min(1.0, self._speed / TAKEOFF_SPEED)
        wave = math.sin((time.perf_counter() - self._t0) * 2.2)
        return max(0, round(airborne * (c.hover + c.bob * wave) * self._scale))

    # --- behaviour -------------------------------------------------------------------

    def _begin_phase(self):
        """Pick what to do next: wander at some speed, stand around, or turn back."""
        roll = random.random()
        if self._walking:
            if roll < 0.35:
                self._walking, self._phase_left = False, random.uniform(3.0, 9.0)
                if random.random() < 0.3:
                    self._dir = -self._dir
            elif roll < 0.45:
                self._dir = -self._dir
                self._phase_left = random.uniform(5.0, 12.0)
            else:
                self._phase_left = random.uniform(5.0, 14.0)
        else:
            self._walking = True
            if random.random() < 0.3:
                self._dir = -self._dir
            self._phase_left = random.uniform(6.0, 14.0)
        self._target = random.uniform(MIN_SPEED, MAX_SPEED) if self._walking else 0.0

    def _tick(self):
        now = time.perf_counter()
        dt = min(now - self._last, 0.1)
        self._last = now
        if self._gone:
            return

        # being stroked or pointed at: stand still (but never in the middle of a dash)
        petted = (now < self._petted_until or now < self._hover_until) and self._sprint_left <= 0
        self._phase_left -= dt
        if self._sprint_left > 0:
            self._sprint_left -= dt
            if self._sprint_left <= 0:  # dash over, back to the normal stroll, same way it was heading
                heading = self._dir
                self._walking = False
                self._begin_phase()
                self._dir = heading
        elif self._phase_left <= 0 and not (self.hold or petted):
            self._begin_phase()

        target = 0.0 if (self.hold or petted) else self._target
        if self._sprint_left > 0:
            accel = SPRINT_ACCEL
        elif self._speed > MAX_SPEED * 1.5 and not self._away:
            accel = SPRINT_BRAKE  # settle down quickly after a dash
        else:
            accel = ACCEL
        step = accel * dt
        self._speed += max(-step, min(step, target - self._speed))

        ag = self._area()
        left, right = ag.left(), ag.right() + 1 - self.width()
        if self._speed > 0.5:
            self._x += self._dir * self._speed * dt
            if self._away:
                if self._x <= left - self.width() or self._x >= right + self.width():
                    self._gone, self._speed = True, 0.0  # fully past the edge
                    self.hide()
                    return
            elif not self._entering and (self._x <= left or self._x >= right):
                self._x = min(max(self._x, left), right)
                self._dir = -self._dir
                self._speed *= 0.2  # slow right down before heading back
        if self._entering and left <= self._x <= right:
            self._entering = False
        self._facing = self._dir
        self._advance_frame(dt)
        self._place()
        state = (self._frame, self._facing, self._lift())
        if state != self._shown_state:  # repaint only when the picture actually changes
            self._shown_state = state
            self.update()
        self._update_interactivity()

    # --- mouse: pet it ---------------------------------------------------------------

    def _pixmap(self):
        frames = self.char.frames if self._facing > 0 else self.char.frames_flipped
        return frames[self._frame % len(frames)]

    def _sprite_origin(self, pix):
        return (self.width() - pix.width()) // 2, self.height() - pix.height() - self._lift()

    def _over_sprite(self, global_pos):
        """True when the point is on a visible (non-transparent) pixel of the character."""
        local = self.mapFromGlobal(global_pos)
        if not self.rect().contains(local):
            return False
        pix = self._pixmap()
        ox, oy = self._sprite_origin(pix)
        x, y = local.x() - ox, local.y() - oy
        if not (0 <= x < pix.width() and 0 <= y < pix.height()):
            return False
        key = (self._facing > 0, self._frame % len(self.char.frames))
        if key not in self._hit_cache:
            self._hit_cache[key] = pix.toImage()
        return self._hit_cache[key].pixelColor(x, y).alpha() > 40

    def _set_click_through(self, on):
        if on == self._click_through or _user32 is None:
            return
        self._click_through = on
        hwnd = int(self.winId())
        style = _user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = (style | WS_EX_TRANSPARENT) if on else (style & ~WS_EX_TRANSPARENT)
        _user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    def _update_interactivity(self):
        """Take the mouse only when the *user* moves the pointer onto the character.

        When the pointer sits still and the character walks under it, the window must stay
        click-through: otherwise the visible and transparent pixels take turns under the pointer,
        the window flips between taking and ignoring the mouse many times a second, and whatever
        is underneath (a text box, a panel) flickers and the cursor shape jumps."""
        if not self.clickable or self._away:
            self._grabbed = False
            self._set_click_through(True)
            return
        now = time.perf_counter()
        if not _mouse_button_down():
            self._pressing = False
        elif not self._pressing:
            self._grabbed = False
            self._set_click_through(True)  # a drag that began in another app must pass through
            return
        if self._pressing:
            return
        pointer = QCursor.pos()
        if pointer != self._pointer:
            self._pointer, self._pointer_moved_at = pointer, now
        over = self._over_sprite(pointer)
        if self._grabbed:
            if over:
                self._off_since = None
                self._hover_until = now + 0.3  # stay put while it is being pointed at
            elif self._off_since is None:
                self._off_since = now
            elif now - self._off_since >= HOVER_RELEASE_AFTER:  # off it for good, not a flicker
                self._grabbed = False
                self._set_click_through(True)
        elif over and now - self._pointer_moved_at <= HOVER_MOVE_WINDOW:
            self._grabbed, self._off_since = True, None
            self._hover_until = now + 0.3
            self._set_click_through(False)

    def showEvent(self, event):
        super().showEvent(event)
        self._click_through = None
        self._set_click_through(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.clickable:
            self._pressing = True
            self._pet()

    def mouseReleaseEvent(self, event):
        self._pressing = False

    def _sprite_top(self):
        pix = self._pixmap()
        return QPoint(self.x() + self.width() // 2, self.y() + self._sprite_origin(pix)[1])

    def _pet(self):
        """A click: hearts, and the character stays put. Many clicks in a row are too much."""
        now = time.perf_counter()
        self._streak = self._streak + 1 if now - self._last_click <= PET_CHAIN else 1
        self._last_click = now
        if self._streak >= OVERWHELM_AT:
            self.hearts.emit(10, self._sprite_top())
            self._streak = 0
            self._start_sprint()
            return
        self._petted_until = now + PET_REST
        self.hearts.emit(min(self._streak, 6), self._sprite_top())

    def _start_sprint(self):
        """Overwhelmed by all the love: dash off to the side with more room, then carry on."""
        ag = self._area()
        centre = self._x + self.width() / 2
        self._dir = 1 if centre < (ag.left() + ag.right()) / 2 else -1
        room = (ag.right() - centre) if self._dir > 0 else (centre - ag.left())
        distance = min(max(ag.width() * SPRINT_SCREEN_SHARE, SPRINT_MIN_DISTANCE), SPRINT_MAX_DISTANCE, room - 60)
        speed = max(SPRINT_MIN_SPEED, SPRINT_BODY_LENGTHS_PER_SECOND * self.width())
        self._petted_until = self._hover_until = 0.0
        self._sprint_left = max(0.4, distance / speed)
        self._walking, self._target, self._phase_left = True, speed, 1e9

    def _advance_frame(self, dt):
        frames = len(self.char.frames)
        if self.char.floating:
            self._frame_clock += dt
            if self._frame_clock >= self.char.frame_ms / 1000:
                self._frame_clock = 0
                self._frame = (self._frame + 1) % frames
            return
        walk = self.char.walk_frames
        if self._speed > 6:
            self._fidget_left = 0
            if self._frame not in walk:
                self._frame, self._step = walk[0], 0
            # Steps follow the pace of the stroll, within sensible limits.
            interval = (self.char.frame_ms / 1000) * min(max(30.0 / self._speed, 0.4), 1.8)  # legs flail in a dash
            self._frame_clock += dt
            if self._frame_clock >= interval:
                self._frame_clock = 0
                self._step = (self._step + 1) % len(walk)
                self._frame = walk[self._step]
            return
        # Standing: rest on the idle frame, and (if the character does it) shuffle now and then.
        if self._fidget_left > 0:
            self._frame_clock += dt
            if self._frame_clock >= self.char.fidget_step:
                self._frame_clock = 0
                self._fidget_left -= 1
                seq = self.char.fidget_frames
                if self._fidget_left == 0:
                    self._frame = self.char.idle_frame
                else:
                    self._frame = seq[len(seq) - self._fidget_left]
        else:
            self._frame = self.char.idle_frame
            if self.char.fidget:
                self._next_fidget -= dt
                if self._next_fidget <= 0:
                    seq = self.char.fidget_frames
                    self._fidget_left = len(seq)
                    self._frame = seq[0]
                    self._frame_clock = 0
                    self._next_fidget = random.uniform(*self.char.fidget_interval)

    # --- painting --------------------------------------------------------------------

    def paintEvent(self, _event):
        pix = self._pixmap()
        painter = QPainter(self)
        painter.drawPixmap(*self._sprite_origin(pix), pix)
