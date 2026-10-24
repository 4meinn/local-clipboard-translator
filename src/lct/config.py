import json
import logging
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from PySide6.QtCore import QObject, Signal

log = logging.getLogger(__name__)

MAX_CHARS = 3000
LONG_TEXT_CHARS = 200


def data_dir():
    base = Path(os.environ.get("APPDATA") or Path.home())
    path = base / "LocalClipboardTranslator"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class Settings:
    lang_a: str = "tr"
    lang_b: str = "de"
    character: str = "berry"
    scale: int = 3
    bubble_seconds: float = 6.0
    selectable: bool = False
    model: str = ""  # empty means pick the best installed model automatically
    ui_language: str = "auto"
    autostart: bool = False
    paused: bool = False


class SettingsStore(QObject):
    changed = Signal(str)

    def __init__(self, path=None):
        super().__init__()
        self._path = Path(path) if path else data_dir() / "settings.json"
        self.first_run = not self._path.exists()
        self.values = Settings()
        self._load()

    def _load(self):
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        known = {f.name: f for f in fields(Settings)}
        for key, value in raw.items():
            if key in known and isinstance(value, type(getattr(self.values, key))):
                setattr(self.values, key, value)

    def _save(self):
        try:
            self._path.write_text(json.dumps(asdict(self.values), indent=2), encoding="utf-8")
        except OSError:
            log.exception("could not save settings")

    def __getattr__(self, name):
        if name in ("values", "_path", "first_run"):
            raise AttributeError(name)
        return getattr(self.values, name)

    def set(self, key, value):
        if getattr(self.values, key) == value:
            return
        setattr(self.values, key, value)
        self._save()
        self.changed.emit(key)
