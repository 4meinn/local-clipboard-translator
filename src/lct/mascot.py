import math
import random
import time

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QPainter
from PySide6.QtWidgets import QWidget

from lct.sprites import load_character

ACCEL = 140.0  # px/s^2, so starts, stops and turns look gradual
MIN_SPEED, MAX_SPEED = 22.0, 95.0


class Mascot(QWidget):
    """A frameless sprite that strolls along the taskbar.

    It ignores the mouse completely (WindowTransparentForInput). A window that takes mouse
    events makes Windows re-evaluate the cursor every time it moves under the pointer, which
    showed up as the cursor flickering while typing near the bottom of the screen.
    """

    moved = Signal(QPoint)  # global position of the top centre of the sprite

    def __init__(self, char_id, scale):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                         | Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.char = None
        self._shown_state = None  # what was last painted, to skip identical repaints
        self._pos = None  # last window position handed to the system
        self.hold = False  # stand still, e.g. while a bubble is open
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
        self._timer.start(33)  # ~30 fps is plenty for a sprite that moves under 100 px/s

    def set_character(self, char_id, scale):
        self.char = load_character(char_id, scale)
        w = max(p.width() for p in self.char.frames)
        h = max(p.height() for p in self.char.frames)
        self._bob = 3 * scale if self.char.floating else 0
        self.setFixedSize(w, h + self._bob * 2)
        self._frame = 0
        self._pos = None  # force a move and an anchor update for the new size
        self._shown_state = None
        self._place()
        self.update()

    def _area(self):
        screen = QGuiApplication.primaryScreen()
        return screen.availableGeometry()

    def _ground_y(self):
        return self._area().bottom() + 1 - self.height()

    def _place(self):
        ag = self._area()
        self._x = min(max(self._x, ag.left()), ag.right() + 1 - self.width())
        pos = (round(self._x), self._ground_y())
        if pos != self._pos:  # touching the window when nothing changed only causes flicker
            self._pos = pos
            self.move(*pos)
            self.moved.emit(QPoint(pos[0] + self.width() // 2, pos[1] + self._bob))

    def _bob_offset(self):
        if not self.char.floating:
            return 0
        return round(self._bob * math.sin((time.perf_counter() - self._t0) * 2.2))

    # --- behaviour -------------------------------------------------------------------

    def _begin_phase(self):
        """Pick what to do next: wander at some speed, stand around, or turn back."""
        roll = random.random()
        if self._walking:
            if roll < 0.40:
                self._walking, self._phase_left = False, random.uniform(1.5, 6.0)
                if random.random() < 0.4:
                    self._dir = -self._dir
            elif roll < 0.60:
                self._dir = -self._dir
                self._phase_left = random.uniform(2.0, 7.0)
            else:
                self._phase_left = random.uniform(2.5, 9.0)
        else:
            self._walking = True
            if random.random() < 0.4:
                self._dir = -self._dir
            self._phase_left = random.uniform(3.0, 10.0)
        self._target = random.uniform(MIN_SPEED, MAX_SPEED) if self._walking else 0.0

    def _tick(self):
        now = time.perf_counter()
        dt = min(now - self._last, 0.1)
        self._last = now

        self._phase_left -= dt
        if self._phase_left <= 0 and not self.hold:
            self._begin_phase()

        target = 0.0 if self.hold else self._target
        step = ACCEL * dt
        self._speed += max(-step, min(step, target - self._speed))

        ag = self._area()
        left, right = ag.left(), ag.right() + 1 - self.width()
        if self._speed > 0.5:
            self._x += self._dir * self._speed * dt
            if self._x <= left or self._x >= right:
                self._x = min(max(self._x, left), right)
                self._dir = -self._dir
                self._speed *= 0.2  # slow right down before heading back
        self._facing = self._dir
        self._advance_frame(dt)
        self._place()
        state = (self._frame, self._facing, self._bob_offset())
        if state != self._shown_state:  # repaint only when the picture actually changes
            self._shown_state = state
            self.update()

    def _advance_frame(self, dt):
        frames = len(self.char.frames)
        if self.char.floating:
            self._frame_clock += dt
            if self._frame_clock >= self.char.frame_ms / 1000:
                self._frame_clock = 0
                self._frame = (self._frame + 1) % frames
            return
        if self._speed > 6:
            self._fidget_left = 0
            # Legs move faster when the stroll does.
            interval = (self.char.frame_ms / 1000) * (55.0 / max(self._speed, 25.0))
            self._frame_clock += dt
            if self._frame_clock >= interval:
                self._frame_clock = 0
                self._frame = (self._frame + 1) % frames
            return
        # Standing: rest on the first frame, now and then shuffle through the others.
        if self._fidget_left > 0:
            self._frame_clock += dt
            if self._frame_clock >= 0.22:
                self._frame_clock = 0
                self._frame = (self._frame + 1) % frames
                self._fidget_left -= 1
                if self._fidget_left == 0:
                    self._frame = 0
        else:
            self._frame = 0
            self._next_fidget -= dt
            if self._next_fidget <= 0:
                self._fidget_left = frames
                self._next_fidget = random.uniform(3, 8)

    # --- painting --------------------------------------------------------------------

    def paintEvent(self, _event):
        frames = self.char.frames if self._facing > 0 else self.char.frames_flipped
        pix = frames[self._frame % len(frames)]
        painter = QPainter(self)
        x = (self.width() - pix.width()) // 2
        y = self.height() - self._bob - pix.height() + self._bob_offset()
        painter.drawPixmap(x, y, pix)
