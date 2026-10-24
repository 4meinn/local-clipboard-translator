import ctypes
import logging
import sys
import threading
import time
from collections import deque
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QObject, QSize, QTimer, Qt
from PySide6.QtGui import QAction, QGuiApplication, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from lct import __version__
from lct.bubble import Bubble
from lct.config import LONG_TEXT_CHARS, MAX_CHARS, SettingsStore, data_dir
from lct.fullscreen import is_fullscreen_busy
from lct.hearts import HeartsOverlay
from lct.hotkey import HotkeyListener
from lct.mascot import Mascot
from lct.resources import asset_path
from lct.settings_dialog import SettingsWindow
from lct.setup_wizard import SetupWizard, current_state
from lct.strings import FAREWELL, Translator, resolve_ui_language, windows_language
from lct.translator import TranslationJob, unload_all, warm_up

APP_ID = "LocalClipboardTranslator"
UI_LANGUAGE_NAMES = {"en": "English", "tr": "Türkçe"}
DEBOUNCE_MS = 150
DOUBLE_COPY_SECONDS = 1.5  # two copies of the same text within this time count as a request
FAREWELL_MS = 2600  # how long the goodbye bubble stays before the character walks off
FULLSCREEN_POLL_MS = 2000
HISTORY_SIZE = 20


def app_icon():
    return QIcon(str(asset_path("icon.ico")))


def paused_icon():
    """The app icon greyed out, so a paused translator is visible at a glance in the tray."""
    icon, dimmed = app_icon(), QIcon()
    for size in (16, 24, 32, 48):
        dimmed.addPixmap(icon.pixmap(QSize(size, size), QIcon.Mode.Disabled))
    return dimmed


def _shorten(text, limit=28):
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


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
        self.wizard = None
        self.history = deque(maxlen=HISTORY_SIZE)  # (source, translation); only kept in memory
        self.fullscreen = False
        self._setup_offered = False
        self._pause_hinted = False
        self._last_copy = ("", 0.0)  # text and time of the previous copy, for the double-copy mode

        self.mascot = Mascot(store.character, store.scale)
        self.mascot.clickable = store.clickable
        self.hearts = HeartsOverlay()
        self.mascot.hearts.connect(self._release_hearts)
        self.bubble = Bubble()
        self.bubble.seconds = store.bubble_seconds
        self.bubble.selectable = store.selectable
        self.mascot.moved.connect(self.bubble.set_anchor)
        self.bubble.closed.connect(self._bubble_closed)

        self.tray = QSystemTrayIcon(app_icon())
        self.tray.activated.connect(self._tray_activated)
        self._build_menu()
        self.tray.show()

        self.clipboard = QGuiApplication.clipboard()
        self.debounce = QTimer(self, singleShot=True, interval=DEBOUNCE_MS)
        self.debounce.timeout.connect(self._clipboard_settled)
        self.clipboard.dataChanged.connect(self.debounce.start)
        store.changed.connect(self._setting_changed)

        self.hotkeys = HotkeyListener(self._hotkey_pressed)
        app.installNativeEventFilter(self.hotkeys)
        app.aboutToQuit.connect(self.hotkeys.unregister)
        self._apply_hotkey()

        self.leave_timer = QTimer(self, singleShot=True)
        self.leave_timer.timeout.connect(self._leave)
        self.fullscreen_timer = QTimer(self, interval=FULLSCREEN_POLL_MS)
        self.fullscreen_timer.timeout.connect(self._poll_fullscreen)
        self.fullscreen_timer.start()

        self.mascot.show()
        QTimer.singleShot(2000, self._warm_up)  # load the model while the user is still settling in

    def _release_hearts(self, count, anchor):
        char = self.mascot.char
        self.hearts.spawn(count, anchor, char.main_color, char.heart_style, self.store.scale)

    def _warm_up(self, unload_first=False):
        """Load the model in the background so the first translation does not wait for it."""
        s = self.store
        def work():
            if unload_first:
                unload_all()  # Ollama keeps a loaded model as it is, so drop it before reloading
            warm_up(s.model, s.processor, s.keep_alive_min)
        threading.Thread(target=work, daemon=True).start()

    # --- tray and menus --------------------------------------------------------------

    def _build_menu(self):
        self.tray.setToolTip(self.tr("tray_tooltip_paused" if self.store.paused else "tray_tooltip"))
        self.tray.setIcon(paused_icon() if self.store.paused else app_icon())
        self.menu = QMenu()
        settings = QAction(self.tr("tray_settings"), self.menu)
        settings.triggered.connect(self.show_settings)
        pause = QAction(self.tr("tray_resume" if self.store.paused else "tray_pause"), self.menu)
        pause.triggered.connect(lambda: self.store.set("paused", not self.store.paused))
        setup = QAction(self.tr("tray_setup"), self.menu)
        setup.triggered.connect(self.show_wizard)
        quit_action = QAction(self.tr("tray_quit"), self.menu)
        quit_action.triggered.connect(self.app.quit)
        self.history_menu = self.menu.addMenu(self.tr("tray_history"))
        self.history_menu.aboutToShow.connect(self._fill_history_menu)
        for action in (settings, pause, setup):
            self.menu.addAction(action)
        self.menu.addSeparator()
        self.menu.addAction(quit_action)
        self.tray.setContextMenu(self.menu)

    def _fill_history_menu(self):
        self.history_menu.clear()
        if not self.history:
            empty = self.history_menu.addAction(self.tr("tray_history_empty"))
            empty.setEnabled(False)
            return
        for source, translation in reversed(self.history):
            label = f"{_shorten(source)}  →  {_shorten(translation)}".replace("&", "&&")
            action = self.history_menu.addAction(label)
            action.triggered.connect(lambda _checked=False, t=translation: self._show_text(t))
        self.history_menu.addSeparator()
        self.history_menu.addAction(self.tr("tray_history_clear")).triggered.connect(lambda: self.history.clear())

    def _show_text(self, text):
        """Show a finished text in the bubble again (used for the history)."""
        self._stop_job()
        self.noticed = True
        self.shown_text = text
        self.mascot.hold = True
        self.bubble.begin(len(text) > LONG_TEXT_CHARS)
        self.bubble.append(text)
        self.bubble.finish()

    def _tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_settings()

    def show_settings(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindow(self.store, self.tr, UI_LANGUAGE_NAMES)
            self.settings_window.quit_requested.connect(self.app.quit)
            self.settings_window.setup_requested.connect(self.show_wizard)
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def show_wizard(self):
        wizard = SetupWizard(self.tr)
        wizard.setAttribute(Qt.WA_DeleteOnClose)
        wizard.finished_ok.connect(self._wizard_finished)
        self.wizard = wizard
        wizard.begin()

    def _wizard_finished(self):
        if self.settings_window:
            self.settings_window.refresh_models()
        self._warm_up()

    def offer_setup_once(self):
        """Open the setup wizard when Ollama or a model is missing, at most once per launch.

        Not remembered across launches on purpose: settings survive an uninstall, so a
        remembered "already offered" would keep the wizard from ever showing up again."""
        if self._setup_offered:
            return
        if current_state()[0] != "ready":
            self._setup_offered = True
            self.show_wizard()

    def _setting_changed(self, key):
        s = self.store
        if key in ("character", "scale"):
            self.mascot.set_character(s.character, s.scale)
        elif key == "clickable":
            self.mascot.clickable = s.clickable
        elif key == "bubble_seconds":
            self.bubble.seconds = s.bubble_seconds
        elif key == "selectable":
            self.bubble.selectable = s.selectable
        elif key == "processor":
            self._stop_job()
            self._warm_up(unload_first=True)  # reload on the new processor
        elif key == "model":
            self._warm_up()
        elif key in ("trigger", "hotkey"):
            self._apply_hotkey()
        elif key == "pause_fullscreen":
            self._poll_fullscreen()
        elif key == "paused":
            self._pause_hinted = False
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

    def _clipboard_text(self):
        """The copied text, or None when there is nothing worth translating."""
        mime = self.clipboard.mimeData()
        if mime is None or not mime.hasText():
            return None
        # Password managers flag their clipboard entries so that tools like this one skip them.
        if any("ExcludeClipboardContentFromMonitorProcessing" in f for f in mime.formats()):
            return None
        text = mime.text().strip()
        if not text or not any(ch.isalpha() for ch in text):
            return None
        return text

    def _active(self):
        """Translating is off while paused by the user, or while a fullscreen app is in front."""
        return not self.store.paused and not self.fullscreen

    def _clipboard_settled(self):
        mode = self.store.trigger
        if mode == "hotkey":
            return  # in hotkey mode copying alone never translates
        text = self._clipboard_text()
        if text is None:
            return
        if self.store.paused:
            if not self._pause_hinted:  # say so once, so a forgotten pause does not look like a bug
                self._pause_hinted = True
                self._say(self.tr("msg_paused"))
            return
        if not self._active():
            return
        if self.bubble.isVisible() and text in self.shown_text:
            return  # the user copied from our own bubble
        if mode == "double":
            previous, when = self._last_copy
            now = time.monotonic()
            self._last_copy = (text, now)
            if text != previous or now - when > DOUBLE_COPY_SECONDS:
                return  # first copy: wait for the second
            self._last_copy = ("", 0.0)
        self._translate(text)

    def _say(self, text):
        self.mascot.hold = True
        self.bubble.notice(text)

    def _hotkey_pressed(self):
        if self.store.paused:
            self._say(self.tr("msg_paused"))  # pressing the hotkey is explicit, so always answer
            return
        if not self._active():
            return
        text = self._clipboard_text()
        if text is not None:
            self._translate(text)

    def _apply_hotkey(self):
        if self.store.trigger != "hotkey":
            self.hotkeys.unregister()
        elif not self.hotkeys.register(self.store.hotkey):
            self.mascot.hold = True
            self.bubble.notice(self.tr("msg_hotkey_busy", key=self.store.hotkey))

    def _poll_fullscreen(self):
        busy = self.store.pause_fullscreen and is_fullscreen_busy()
        if busy == self.fullscreen:
            return
        self.fullscreen = busy
        if busy:
            self._stop_job()
            self._say_goodbye()
        else:
            self.leave_timer.stop()
            self.mascot.set_away(False)

    def _say_goodbye(self):
        """A short farewell in the Windows language, then the walk off screen."""
        self.mascot.hold = True
        self.noticed = True
        self.shown_text = FAREWELL[windows_language()]
        self.bubble.notice(self.shown_text)
        self.leave_timer.start(FAREWELL_MS)

    def _leave(self):
        if self.fullscreen:
            self.bubble.close_now()  # nothing should linger over the game
            self.mascot.set_away(True)

    def _translate(self, text):
        self._stop_job()
        self.shown_text = ""
        if len(text) > MAX_CHARS:
            self.mascot.hold = True
            self.bubble.notice(self.tr("msg_too_long", n=len(text), max=MAX_CHARS))
            return
        self.noticed = False
        self.mascot.hold = True
        self.bubble.show_thinking()
        job = TranslationJob(text, self.store.lang_a, self.store.lang_b, self.store.model, self.tr,
                             self.store.processor, self.store.keep_alive_min)
        job.started_translation.connect(self._on_started)
        job.text_delta.connect(self._on_delta)
        job.notice.connect(self._on_notice)
        job.setup_needed.connect(self._on_setup_needed)
        job.loading_model.connect(self._on_loading_model)
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

    def _on_loading_model(self):
        if self._current():
            self.bubble.show_status(self.tr("msg_loading_model"))

    def _on_setup_needed(self):
        if self._current():
            self.offer_setup_once()

    def _on_notice(self, text):
        if self._current():
            self.noticed = True
            self.shown_text = text
            self.bubble.notice(text)

    def _on_finished(self):
        job = self.sender()
        if self._current() and not self.noticed:
            self.bubble.finish()
            translation = self.shown_text.strip()
            if translation:
                self.history.append((job.text, translation))
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
    app.setWindowIcon(app_icon())
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
    QTimer.singleShot(1500, controller.offer_setup_once)
    logging.getLogger(__name__).info("started v%s, languages %s/%s", __version__, store.lang_a, store.lang_b)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
