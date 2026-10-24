import ctypes
import logging
import sys
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QObject, QTimer, Qt
from PySide6.QtGui import QAction, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from lct import __version__
from lct.bubble import Bubble
from lct.config import MAX_CHARS, SettingsStore, data_dir
from lct.mascot import Mascot
from lct.settings_dialog import SettingsWindow
from lct.sprites import load_character
from lct.strings import STRINGS, Translator, resolve_ui_language
from lct.translator import TranslationJob

APP_ID = "LocalClipboardTranslator"
UI_LANGUAGE_NAMES = {"en": "English", "tr": "Türkçe"}
DEBOUNCE_MS = 150


def character_icon(char_id):
    pix = load_character(char_id, 2).frames[0]
    canvas = QPixmap(48, 48)
    canvas.fill(Qt.transparent)
    painter = QPainter(canvas)
    painter.drawPixmap((48 - pix.width()) // 2, 48 - pix.height() - 2, pix)
    painter.end()
    return QIcon(canvas)


class Controller(QObject):
    def __init__(self, app, store):
        super().__init__()
        self.app, self.store = app, store
        self.tr = Translator(resolve_ui_language(store.ui_language))
        self.job = None
        self.jobs = set()  # keeps finished-but-not-yet-collected threads alive
        self.noticed = False
        self.shown_text = ""
        self.settings_window = None

        self.mascot = Mascot(store.character, store.scale)
        self.bubble = Bubble()
        self.bubble.seconds = store.bubble_seconds
        self.bubble.selectable = store.selectable
        self.mascot.moved.connect(self.bubble.set_anchor)
        self.mascot.clicked.connect(self.bubble.close_now)
        self.mascot.menu_requested.connect(self._show_menu)
        self.bubble.closed.connect(self._bubble_closed)

        self.tray = QSystemTrayIcon(character_icon(store.character))
        self.tray.activated.connect(self._tray_activated)
        self._build_menu()
        self.tray.show()

        self.clipboard = QGuiApplication.clipboard()
        self.debounce = QTimer(self, singleShot=True, interval=DEBOUNCE_MS)
        self.debounce.timeout.connect(self._clipboard_settled)
        self.clipboard.dataChanged.connect(self.debounce.start)
        store.changed.connect(self._setting_changed)

        self.mascot.show()

    # --- tray and menus --------------------------------------------------------------

    def _build_menu(self):
        self.tray.setToolTip(self.tr("tray_tooltip"))
        self.menu = QMenu()
        settings = QAction(self.tr("tray_settings"), self.menu)
        settings.triggered.connect(self.show_settings)
        pause = QAction(self.tr("tray_resume" if self.store.paused else "tray_pause"), self.menu)
        pause.triggered.connect(lambda: self.store.set("paused", not self.store.paused))
        quit_action = QAction(self.tr("tray_quit"), self.menu)
        quit_action.triggered.connect(self.app.quit)
        for action in (settings, pause):
            self.menu.addAction(action)
        self.menu.addSeparator()
        self.menu.addAction(quit_action)
        self.tray.setContextMenu(self.menu)

    def _show_menu(self, pos):
        self.menu.popup(pos)

    def _tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_settings()

    def show_settings(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindow(self.store, self.tr, UI_LANGUAGE_NAMES)
            self.settings_window.setWindowIcon(character_icon(self.store.character))
            self.settings_window.quit_requested.connect(self.app.quit)
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def _setting_changed(self, key):
        s = self.store
        if key in ("character", "scale"):
            self.mascot.set_character(s.character, s.scale)
            self.tray.setIcon(character_icon(s.character))
            if self.settings_window:
                self.settings_window.setWindowIcon(character_icon(s.character))
        elif key == "bubble_seconds":
            self.bubble.seconds = s.bubble_seconds
        elif key == "selectable":
            self.bubble.selectable = s.selectable
        elif key == "paused":
            self._build_menu()
            if s.paused:
                self._stop_job()
                self.bubble.close_now()
        elif key == "ui_language":
            self.tr = Translator(resolve_ui_language(s.ui_language))
            self._build_menu()
            if self.settings_window:  # rebuild it so every label follows the new language
                old, self.settings_window = self.settings_window, None
                old.deleteLater()
                QTimer.singleShot(0, self.show_settings)

    # --- clipboard -> translation ----------------------------------------------------

    def _clipboard_settled(self):
        if self.store.paused:
            return
        mime = self.clipboard.mimeData()
        if mime is None or not mime.hasText():
            return
        # Password managers flag their clipboard entries so that tools like this one skip them.
        if any("ExcludeClipboardContentFromMonitorProcessing" in f for f in mime.formats()):
            return
        text = mime.text().strip()
        if not text or not any(ch.isalpha() for ch in text):
            return
        if self.bubble.isVisible() and text in self.shown_text:
            return  # the user copied from our own bubble
        self._stop_job()
        self.shown_text = ""
        if len(text) > MAX_CHARS:
            self.mascot.hold = True
            self.bubble.notice(self.tr("msg_too_long", n=len(text), max=MAX_CHARS))
            return
        self.noticed = False
        self.mascot.hold = True
        self.bubble.show_thinking()
        job = TranslationJob(text, self.store.lang_a, self.store.lang_b, self.store.model, self.tr)
        job.started_translation.connect(self._on_started)
        job.text_delta.connect(self._on_delta)
        job.notice.connect(self._on_notice)
        job.finished.connect(self._on_finished)
        self.jobs.add(job)
        self.job = job
        job.start()

    def _stop_job(self):
        if self.job is not None:
            self.job.cancel()
            self.job = None

    def _current(self):
        return self.job is not None and self.sender() is self.job

    def _on_started(self, long):
        if self._current():
            self.bubble.begin(long)

    def _on_delta(self, text):
        if self._current():
            self.shown_text += text
            self.bubble.append(text)

    def _on_notice(self, text):
        if self._current():
            self.noticed = True
            self.shown_text = text
            self.bubble.notice(text)

    def _on_finished(self):
        job = self.sender()
        if self._current() and not self.noticed:
            self.bubble.finish()
        job.wait()
        self.jobs.discard(job)

    def _bubble_closed(self):
        self._stop_job()
        self.mascot.hold = False
        self.shown_text = ""


def _single_instance(server_name):
    """Return a QLocalServer if we are the first instance, or None after pinging the first one."""
    sock = QLocalSocket()
    sock.connectToServer(server_name)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.waitForBytesWritten(300)
        return None
    QLocalServer.removeServer(server_name)
    server = QLocalServer()
    server.listen(server_name)
    return server


def _setup_logging():
    handler = RotatingFileHandler(data_dir() / "app.log", maxBytes=200_000, backupCount=1, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def main():
    _setup_logging()
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MetinBerkaySen." + APP_ID)
    except (AttributeError, OSError):
        pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP_ID)
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")

    server = _single_instance(APP_ID + "-instance")
    if server is None:
        return 0

    store = SettingsStore()
    first_run = store.first_run
    controller = Controller(app, store)
    server.newConnection.connect(lambda: (server.nextPendingConnection(), controller.show_settings()))
    if first_run:
        controller.show_settings()
    logging.getLogger(__name__).info("started v%s, languages %s/%s", __version__, store.lang_a, store.lang_b)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
