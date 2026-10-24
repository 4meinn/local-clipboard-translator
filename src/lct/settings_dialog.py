from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
                               QLabel, QListWidget, QListWidgetItem, QPushButton, QScrollArea, QVBoxLayout,
                               QWidget)

from lct import autostart, translator
from lct.hotkey import HOTKEYS
from lct.languages import NATIVE_NAME, SUPPORTED
from lct.sprites import load_character, load_manifest

ICON = 88


def _icon_for(char_id):
    char = load_character(char_id, 3)
    pix = char.frames[0]
    canvas = QPixmap(ICON, ICON)
    canvas.fill(Qt.transparent)
    painter = QPainter(canvas)
    painter.drawPixmap((ICON - pix.width()) // 2, ICON - pix.height() - 4, pix)
    painter.end()
    return QIcon(canvas)


class SettingsWindow(QWidget):
    quit_requested = Signal()
    setup_requested = Signal()

    def __init__(self, store, tr, ui_language_names):
        super().__init__()
        self.store, self.tr = store, tr
        self.setWindowTitle(tr("win_title"))
        self.setMinimumWidth(640)
        self._loading = True

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()  # keeps the window usable on small screens
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        root = QVBoxLayout(content)

        # Languages
        box = QGroupBox(tr("grp_languages"))
        form = QFormLayout(box)
        self.lang_a, self.lang_b = QComboBox(), QComboBox()
        for combo in (self.lang_a, self.lang_b):
            for code in SUPPORTED:
                combo.addItem(NATIVE_NAME[code], code)
        form.addRow(tr("lbl_lang_a"), self.lang_a)
        form.addRow(tr("lbl_lang_b"), self.lang_b)
        hint = QLabel(tr("lang_hint"))
        hint.setWordWrap(True)
        form.addRow(hint)
        root.addWidget(box)

        # Character
        box = QGroupBox(tr("grp_character"))
        col = QVBoxLayout(box)
        self.characters = QListWidget()
        self.characters.setViewMode(QListWidget.IconMode)
        self.characters.setMovement(QListWidget.Static)
        self.characters.setResizeMode(QListWidget.Adjust)
        self.characters.setIconSize(QSize(ICON, ICON))
        self.characters.setGridSize(QSize(ICON + 24, ICON + 30))
        self.characters.setFixedHeight(2 * (ICON + 30) + 12)
        self.characters.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.characters.setSpacing(2)
        for entry in load_manifest():
            item = QListWidgetItem(_icon_for(entry["id"]), entry["name"])
            item.setData(Qt.UserRole, entry["id"])
            item.setTextAlignment(Qt.AlignHCenter)
            self.characters.addItem(item)
        col.addWidget(self.characters)
        row = QFormLayout()
        self.size = QComboBox()
        for scale in (2, 3, 4, 5):
            self.size.addItem(f"{scale}x", scale)
        row.addRow(tr("lbl_size"), self.size)
        col.addLayout(row)
        root.addWidget(box)

        # Bubble
        box = QGroupBox(tr("grp_bubble"))
        form = QFormLayout(box)
        self.selectable = QCheckBox(tr("chk_selectable"))
        self.duration = QDoubleSpinBox()
        self.duration.setRange(2, 30)
        self.duration.setSingleStep(1)
        self.duration.setDecimals(0)
        self.duration.setSuffix(tr("unit_seconds"))
        form.addRow(self.selectable)
        form.addRow(tr("lbl_duration"), self.duration)
        root.addWidget(box)

        # When to translate
        box = QGroupBox(tr("grp_trigger"))
        form = QFormLayout(box)
        self.trigger = QComboBox()
        for key in ("auto", "double", "hotkey"):
            self.trigger.addItem(tr("trig_" + key), key)
        self.hotkey = QComboBox()
        for name in HOTKEYS:
            self.hotkey.addItem(name, name)
        self.trigger_note = QLabel()
        self.trigger_note.setWordWrap(True)
        self.pause_fullscreen = QCheckBox(tr("chk_pause_fullscreen"))
        form.addRow(self.trigger)
        form.addRow(tr("lbl_hotkey"), self.hotkey)
        form.addRow(self.trigger_note)
        form.addRow(self.pause_fullscreen)
        root.addWidget(box)

        # Model
        box = QGroupBox(tr("grp_model"))
        col = QVBoxLayout(box)
        line = QHBoxLayout()
        self.model = QComboBox()
        self.model.setMinimumWidth(260)
        refresh = QPushButton(tr("btn_refresh"))
        line.addWidget(QLabel(tr("lbl_model")))
        line.addWidget(self.model, 1)
        line.addWidget(refresh)
        col.addLayout(line)
        self.status = QLabel()
        self.status.setWordWrap(True)
        col.addWidget(self.status)
        setup = QPushButton(tr("btn_setup"))
        setup.clicked.connect(self.setup_requested)
        col.addWidget(setup, 0, Qt.AlignLeft)
        root.addWidget(box)

        # Performance
        box = QGroupBox(tr("grp_performance"))
        form = QFormLayout(box)
        self.processor = QComboBox()
        self.processor.addItem(tr("proc_gpu"), "gpu")
        self.processor.addItem(tr("proc_cpu"), "cpu")
        self.proc_note = QLabel()
        self.proc_note.setWordWrap(True)
        self.keep_alive = QComboBox()
        for minutes in (1, 5, 10, 30, 60):
            self.keep_alive.addItem(f"{minutes}{tr('unit_minutes')}", minutes)
        self.running = QLabel()
        self.running.setWordWrap(True)
        form.addRow(tr("lbl_processor"), self.processor)
        form.addRow(self.proc_note)
        form.addRow(tr("lbl_keep_alive"), self.keep_alive)
        form.addRow(self.running)
        root.addWidget(box)

        # General
        box = QGroupBox(tr("grp_general"))
        form = QFormLayout(box)
        self.autostart = QCheckBox(tr("chk_autostart"))
        self.ui_language = QComboBox()
        self.ui_language.addItem(tr("ui_auto"), "auto")
        for code, name in ui_language_names.items():
            self.ui_language.addItem(name, code)
        form.addRow(self.autostart)
        form.addRow(tr("lbl_ui_language"), self.ui_language)
        root.addWidget(box)

        footer = QHBoxLayout()
        footer.addWidget(QLabel(tr("hint_copy")), 1)
        quit_button = QPushButton(tr("tray_quit"))
        footer.addWidget(quit_button)
        root.addLayout(footer)

        self._load_values()
        self._loading = False
        hint = content.sizeHint()
        available = QGuiApplication.primaryScreen().availableGeometry().height()
        self.resize(hint.width() + 4, min(hint.height() + 4, available - 80))

        self.lang_a.currentIndexChanged.connect(lambda: self._language_changed("lang_a"))
        self.lang_b.currentIndexChanged.connect(lambda: self._language_changed("lang_b"))
        self.characters.currentItemChanged.connect(self._character_changed)
        self.size.currentIndexChanged.connect(lambda: self._set("scale", self.size.currentData()))
        self.selectable.toggled.connect(lambda v: self._set("selectable", v))
        self.duration.valueChanged.connect(lambda v: self._set("bubble_seconds", float(v)))
        self.model.currentIndexChanged.connect(lambda: self._set("model", self.model.currentData() or ""))
        self.trigger.currentIndexChanged.connect(self._trigger_changed)
        self.hotkey.currentIndexChanged.connect(lambda: self._set("hotkey", self.hotkey.currentData()))
        self.pause_fullscreen.toggled.connect(lambda v: self._set("pause_fullscreen", v))
        self.processor.currentIndexChanged.connect(self._processor_changed)
        self.keep_alive.currentIndexChanged.connect(lambda: self._set("keep_alive_min", self.keep_alive.currentData()))
        self.autostart.toggled.connect(self._autostart_changed)
        self.ui_language.currentIndexChanged.connect(lambda: self._set("ui_language", self.ui_language.currentData()))
        refresh.clicked.connect(self.refresh_models)
        quit_button.clicked.connect(self.quit_requested)

    def _load_values(self):
        s = self.store
        self.lang_a.setCurrentIndex(self.lang_a.findData(s.lang_a))
        self.lang_b.setCurrentIndex(self.lang_b.findData(s.lang_b))
        for i in range(self.characters.count()):
            if self.characters.item(i).data(Qt.UserRole) == s.character:
                self.characters.setCurrentRow(i)
        self.size.setCurrentIndex(max(0, self.size.findData(s.scale)))
        self.selectable.setChecked(s.selectable)
        self.duration.setValue(s.bubble_seconds)
        self.trigger.setCurrentIndex(max(0, self.trigger.findData(s.trigger)))
        self.hotkey.setCurrentIndex(max(0, self.hotkey.findData(s.hotkey)))
        self.pause_fullscreen.setChecked(s.pause_fullscreen)
        self._update_trigger_note()
        self.processor.setCurrentIndex(max(0, self.processor.findData(s.processor)))
        self.keep_alive.setCurrentIndex(max(0, self.keep_alive.findData(s.keep_alive_min)))
        self._update_processor_note()
        self.autostart.setChecked(autostart.is_enabled())
        self.ui_language.setCurrentIndex(max(0, self.ui_language.findData(s.ui_language)))
        self.refresh_models()

    def refresh_models(self):
        was_loading, self._loading = self._loading, True
        self.model.clear()
        self.model.addItem(self.tr("model_auto"), "")
        try:
            names = translator.list_models()
            self.status.setText(self.tr("status_ok", n=len(names)))
        except translator.OllamaUnavailable:
            names = []
            self.status.setText(self.tr("status_down"))
        if self.store.model and self.store.model not in names:
            names.append(self.store.model)
        for name in names:
            self.model.addItem(name, name)
        self.model.setCurrentIndex(max(0, self.model.findData(self.store.model)))
        self._loading = was_loading
        self._update_running()

    def _update_running(self):
        """Say where the model really runs, as reported by Ollama (it may fall back to the CPU)."""
        try:
            loaded = translator.running_models()
        except (translator.OllamaUnavailable, translator.OllamaError):
            loaded = []
        if not loaded:
            self.running.setText(self.tr("run_none"))
            return
        name, vram = loaded[0]
        if vram >= 0.99:
            self.running.setText(self.tr("run_gpu", model=name))
        elif vram <= 0.01:
            self.running.setText(self.tr("run_cpu", model=name))
        else:
            self.running.setText(self.tr("run_mixed", model=name, pct=round(vram * 100)))

    def _update_trigger_note(self):
        mode = self.trigger.currentData()
        self.trigger_note.setText(self.tr("note_trig_" + mode))
        self.hotkey.setEnabled(mode == "hotkey")

    def _trigger_changed(self):
        self._update_trigger_note()
        self._set("trigger", self.trigger.currentData())

    def _update_processor_note(self):
        self.proc_note.setText(self.tr("note_cpu" if self.processor.currentData() == "cpu" else "note_gpu"))

    def _processor_changed(self):
        self._update_processor_note()
        self._set("processor", self.processor.currentData())

    def _set(self, key, value):
        if not self._loading:
            self.store.set(key, value)

    def _language_changed(self, which):
        """The two languages must differ: picking the other one's language swaps them."""
        if self._loading:
            return
        a, b = self.lang_a.currentData(), self.lang_b.currentData()
        if a == b:
            other = self.lang_b if which == "lang_a" else self.lang_a
            previous = self.store.lang_a if which == "lang_a" else self.store.lang_b
            self._loading = True
            other.setCurrentIndex(other.findData(previous))  # swap: the other side takes the old value
            self._loading = False
            a, b = self.lang_a.currentData(), self.lang_b.currentData()
        self.store.set("lang_a", a)
        self.store.set("lang_b", b)

    def _character_changed(self, item, _previous):
        if item is not None:
            self._set("character", item.data(Qt.UserRole))

    def _autostart_changed(self, enabled):
        if not self._loading:
            autostart.set_enabled(enabled)
            self.store.set("autostart", enabled)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._loading:
            self.refresh_models()  # Ollama or the loaded model may have changed meanwhile

    def closeEvent(self, event):
        event.ignore()  # the app lives in the tray, closing only hides the window
        self.hide()
