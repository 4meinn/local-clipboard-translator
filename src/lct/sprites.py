import json
from dataclasses import dataclass, field

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QImage, QPixmap

from lct.resources import asset_path

# Per-character quirks: floating characters bob and flap instead of walking, and some
# sheets list frames that read better as a slower cycle.
PROFILES = {
    "balloon": {"floating": True, "frame_ms": 380},
}


@dataclass
class Character:
    id: str
    name: str
    frames: list = field(default_factory=list)  # facing right
    frames_flipped: list = field(default_factory=list)  # facing left
    floating: bool = False
    frame_ms: int = 140


def load_manifest():
    return json.loads(asset_path("characters", "characters.json").read_text(encoding="utf-8"))


def load_character(char_id, scale):
    entry = next(e for e in load_manifest() if e["id"] == char_id)
    strip = QImage(str(asset_path("characters", f"{char_id}.png")))
    w, h = entry["frame_width"], entry["frame_height"]
    char = Character(id=entry["id"], name=entry["name"], **PROFILES.get(char_id, {}))
    for i in range(entry["frames"]):
        frame = strip.copy(QRect(i * w, 0, w, h))
        frame = frame.scaled(w * scale, h * scale, Qt.IgnoreAspectRatio, Qt.FastTransformation)
        char.frames.append(QPixmap.fromImage(frame))
        char.frames_flipped.append(QPixmap.fromImage(frame.mirrored(True, False)))
    return char
