import math

from PySide6.QtCore import QPoint, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

PAD = 12
TAIL = 10
RADIUS = 10
MAX_WIDTH = 420  # text width of a short bubble
LONG_WIDTH = 440
LONG_HEIGHT = 132  # about six lines of the scrolling view
SCROLL_SPEED = 16.0  # px per second, roughly a comfortable reading pace
FADE_MS = 900


class Bubble(QWidget):
    """Speech bubble above the mascot.

    Short translations stream in and fade out on their own. Long ones scroll upwards like
    end credits while the rest is still being translated. A click on the bubble closes it.
    """

    closed = Signal()

    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                         | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.seconds = 6.0
        self.selectable = False
        self._anchor = QPoint(0, 0)
        self._tail_x = 0
        self._long = False
        self._streaming = False
        self._width = 0
        self._scroll_pos = 0.0
        self._hold_ms = 0
        self._dots = 0

        self._view = QTextBrowser()
        self._view.setFrameShape(QTextBrowser.NoFrame)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.viewport().setAutoFillBackground(False)
        self._view.setStyleSheet("QTextBrowser { background: transparent; color: #1f1f1f; border: none; }")
        font = QFont("Segoe UI", 11)
        self._view.setFont(font)
        self._view.document().setDocumentMargin(0)
        self._view.setOpenLinks(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(PAD, PAD, PAD, PAD + TAIL)
        layout.addWidget(self._view)

        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(FADE_MS)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self._faded)
        self._hide_timer = QTimer(self, singleShot=True)
        self._hide_timer.timeout.connect(self._start_fade)
        self._scroll_timer = QTimer(self)
        self._scroll_timer.setInterval(33)
        self._scroll_timer.timeout.connect(self._scroll_tick)
        self._dots_timer = QTimer(self)
        self._dots_timer.setInterval(350)
        self._dots_timer.timeout.connect(self._dots_tick)

    # --- public API ------------------------------------------------------------------

    def set_anchor(self, top_center):
        """Global point the tail should point at (top centre of the mascot)."""
        self._anchor = top_center
        if self.isVisible():
            self._place()

    def show_thinking(self):
        self._reset()
        self._view.setPlainText("…")
        self._view.setTextInteractionFlags(Qt.NoTextInteraction)
        self._dots = 0
        self._dots_timer.start()
        self._width = 0
        self._fit()
        self._show()

    def show_status(self, text):
        """A message that stays until the real answer replaces it, e.g. while the model loads."""
        self._reset()
        self._long = False
        self._streaming = True  # keeps the fade timer off until the answer or an error arrives
        self._view.setPlainText(text)
        self._apply_interaction()
        self._width = 0
        self._fit()
        self._show()

    def begin(self, long):
        """The translation is about to stream in. `long` picks the scrolling view."""
        self._dots_timer.stop()
        self._long = long
        self._streaming = True
        self._view.clear()
        self._apply_interaction()
        frame = self._view.document().rootFrame()
        fmt = frame.frameFormat()
        fmt.setTopMargin(LONG_HEIGHT if long else 0)  # long text starts below the view and rises into it
        fmt.setBottomMargin(LONG_HEIGHT * 0.4 if long else 0)
        frame.setFrameFormat(fmt)
        if long:
            self._width = LONG_WIDTH
            self._scroll_pos = 0.0
            self._hold_ms = 0
            self._scroll_timer.start()
        self._fit()
        self._show()

    def append(self, text):
        self._view.moveCursor(self._view.textCursor().MoveOperation.End)
        self._view.insertPlainText(text)
        self._fit()

    def finish(self):
        self._streaming = False
        if not self._long:
            ms = int(self.seconds * 1000 + len(self._view.toPlainText()) * 40)
            self._hide_timer.start(ms)

    def notice(self, text):
        self._reset()
        self._dots_timer.stop()
        self._long = False
        self._streaming = False
        self._view.setPlainText(text)
        self._apply_interaction()
        self._width = 0
        self._fit()
        self._show()
        self._hide_timer.start(int(self.seconds * 1000 + len(text) * 40))

    def close_now(self):
        if not self.isVisible():
            return
        self._reset()
        self.hide()
        self.closed.emit()

    # --- internals -------------------------------------------------------------------

    def _reset(self):
        self._hide_timer.stop()
        self._scroll_timer.stop()
        self._dots_timer.stop()
        self._fade.stop()
        self.setWindowOpacity(1.0)

    def _apply_interaction(self):
        flags = Qt.TextSelectableByMouse if self.selectable else Qt.NoTextInteraction
        self._view.setTextInteractionFlags(flags)
        # When text is not selectable, clicks fall through to the bubble and close it.
        self._view.viewport().setAttribute(Qt.WA_TransparentForMouseEvents, not self.selectable)
        self._view.setAttribute(Qt.WA_TransparentForMouseEvents, not self.selectable)

    def _show(self):
        if not self.isVisible():
            self.setWindowOpacity(1.0)
            self.show()
        self._place()

    def _fit(self):
        doc = self._view.document()
        if self._long:
            self._view.setFixedSize(LONG_WIDTH, LONG_HEIGHT)
            doc.setTextWidth(LONG_WIDTH)
        else:
            doc.setTextWidth(MAX_WIDTH)
            wanted = min(MAX_WIDTH, math.ceil(doc.idealWidth()) + 4)
            self._width = max(self._width, wanted, 40)  # only ever grows while text streams in
            doc.setTextWidth(self._width)
            self._view.setFixedSize(self._width + 2, math.ceil(doc.size().height()) + 2)
        self.adjustSize()
        self.setFixedSize(self.sizeHint())
        if self.isVisible():
            self._place()

    def _place(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = self._anchor.x() - self.width() // 2
        x = min(max(x, screen.left() + 6), screen.right() - self.width() - 6)
        y = self._anchor.y() - self.height() + 2
        self._tail_x = self._anchor.x() - x
        self.move(x, max(y, screen.top() + 4))
        self.update()

    def _dots_tick(self):
        self._dots = (self._dots + 1) % 3
        self._view.setPlainText("." * (self._dots + 1))

    def _scroll_tick(self):
        bar = self._view.verticalScrollBar()
        if abs(bar.value() - min(round(self._scroll_pos), bar.maximum())) > 1:  # user used the wheel
            self._scroll_pos = float(bar.value())
        if self.underMouse():
            return  # hovering pauses the credits so it can be read at leisure
        at_end = bar.value() >= bar.maximum() and bar.maximum() > 0
        if at_end:
            self._scroll_pos = float(bar.maximum())
            if not self._streaming:
                self._hold_ms += self._scroll_timer.interval()
                if self._hold_ms >= 2500:
                    self._scroll_timer.stop()
                    self._start_fade()
            return
        self._hold_ms = 0
        self._scroll_pos += SCROLL_SPEED * self._scroll_timer.interval() / 1000
        bar.setValue(round(self._scroll_pos))

    def _start_fade(self):
        self._fade.start()

    def _faded(self):
        self.hide()
        self.setWindowOpacity(1.0)
        self.closed.emit()

    # --- events ----------------------------------------------------------------------

    def enterEvent(self, event):
        if self._fade.state() == QPropertyAnimation.Running:
            self._fade.stop()
            self.setWindowOpacity(1.0)
        self._hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._streaming and not self._long and self.isVisible():
            self._hide_timer.start(2000)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.close_now()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        body_h = self.height() - TAIL
        path = QPainterPath()
        path.addRoundedRect(1.5, 1.5, self.width() - 3, body_h - 3, RADIUS, RADIUS)
        tail_x = min(max(self._tail_x, RADIUS + TAIL), self.width() - RADIUS - TAIL)
        tail = QPainterPath()
        tail.moveTo(tail_x - TAIL, body_h - 2)
        tail.lineTo(tail_x, self.height() - 1.5)
        tail.lineTo(tail_x + TAIL, body_h - 2)
        path |= tail
        painter.setPen(QPen(QColor("#2b2b2b"), 2.5))
        painter.setBrush(QColor("#fffdf4"))
        painter.drawPath(path)
