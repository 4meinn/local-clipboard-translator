"""Little pixel hearts that float up from the character when you click it."""
import math
import random
import time

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

# o = outline, f = fill, h = highlight, . = nothing
HEART = [
    ".oo...oo.",
    "ohhoooffo",
    "ohffffffo",
    "offfffffo",
    ".offfffo.",
    "..offfo..",
    "...ofo...",
    "....o....",
]
OUTLINE = QColor(32, 24, 30)
SIZE = (360, 240)  # overlay window, wide enough for a burst and tall enough to rise in
LIFE = (2.8, 3.8)  # seconds a heart lives
RISE = (16, 28)  # px per second, a lazy float
FADE_FROM = 0.25  # share of its life a heart stays fully visible before it starts to fade


def _lighter(color, amount=0.55):
    return QColor(int(color.red() + (255 - color.red()) * amount),
                  int(color.green() + (255 - color.green()) * amount),
                  int(color.blue() + (255 - color.blue()) * amount))


_cache = {}


def heart_pixmap(color, style, scale):
    key = (color.rgb(), style, scale)
    if key in _cache:
        return _cache[key]
    fill, light = color, _lighter(color)
    image = QImage(len(HEART[0]), len(HEART), QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    for y, row in enumerate(HEART):
        for x, code in enumerate(row):
            if code == ".":
                continue
            pixel = {"o": OUTLINE, "f": fill, "h": light}[code]
            if style == "robot":
                # CRT look: every other body row is dimmed, like scanlines
                if code in "fh" and y % 2 == 1:
                    pixel = QColor(pixel.red() // 2, pixel.green() // 2, pixel.blue() // 2)
            image.setPixelColor(x, y, pixel)
    pix = QPixmap.fromImage(image.scaled(image.width() * scale, image.height() * scale,
                                         Qt.IgnoreAspectRatio, Qt.FastTransformation))
    _cache[key] = pix
    return pix


class _Heart:
    __slots__ = ("x", "y", "vx", "rise", "age", "life", "delay", "phase", "sway", "pix")

    def __init__(self, x, y, pix):
        self.x, self.y, self.pix = x, y, pix
        self.rise = random.uniform(*RISE)
        self.vx = random.uniform(-4, 4)
        self.life = random.uniform(*LIFE)
        self.age = 0.0
        self.delay = 0.0
        self.phase = random.uniform(0, math.tau)
        self.sway = random.uniform(3, 7)


class HeartsOverlay(QWidget):
    """A click-through window, only shown while there are hearts in the air."""

    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                         | Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(*SIZE)
        self.hearts = []
        self.style = "classic"
        self._last = time.perf_counter()
        self._timer = QTimer(self, interval=16)
        self._timer.timeout.connect(self._tick)

    def spawn(self, count, anchor, color, style, scale):
        """`anchor` is the global point on top of the character the hearts rise from."""
        if not self.hearts:  # a new burst: put the window around the character
            self.move(anchor.x() - SIZE[0] // 2, anchor.y() - SIZE[1] + 24)
        self.style = style
        size = max(2, scale)
        for i in range(count):
            pix = heart_pixmap(color, style, max(2, size - (1 if random.random() < 0.4 else 0)))
            x = anchor.x() - self.x() + random.uniform(-26, 26) - pix.width() / 2
            y = anchor.y() - self.y() - pix.height() - random.uniform(0, 10)
            heart = _Heart(x, y, pix)
            heart.delay = i * random.uniform(0.07, 0.14) if count > 3 else 0.0  # a burst pours out
            self.hearts.append(heart)
        if not self._timer.isActive():
            self._last = time.perf_counter()
            self._timer.start()
        self.show()

    def _tick(self):
        now = time.perf_counter()
        dt, self._last = min(now - self._last, 0.1), now
        for h in self.hearts:
            if h.delay > 0:
                h.delay -= dt
                continue
            h.age += dt
            h.y -= h.rise * dt
            h.x += h.vx * dt
        self.hearts = [h for h in self.hearts if h.age < h.life]
        if not self.hearts:
            self._timer.stop()
            self.hide()
            return
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        for h in self.hearts:
            if h.delay > 0:
                continue
            t = h.age / h.life
            u = min(1.0, max(0.0, (t - FADE_FROM) / (1.0 - FADE_FROM)))
            alpha = 1.0 - u * u * (3.0 - 2.0 * u)  # smoothstep: eases out instead of dropping off
            x = h.x + h.sway * math.sin(h.age * 1.8 + h.phase)
            if self.style == "robot":
                if int(h.age * 16 + h.phase * 3) % 6 == 0:
                    continue  # a flicker, as if the signal drops for a frame
                x += random.choice((-1, 0, 0, 1)) * 2  # glitchy jitter
            painter.setOpacity(alpha)
            painter.drawPixmap(QPoint(round(x), round(h.y)), h.pix)
