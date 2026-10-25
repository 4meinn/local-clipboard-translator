import json
from collections import Counter
from dataclasses import dataclass, field

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QPixmap

from lct.resources import asset_path

# Per-character quirks. Sizes are in sprite pixels, multiplied by the display scale.
#   floating: airborne all the time and flaps instead of walking (hover + bob)
#   flying:   on the ground while standing, rises and bobs while moving
#   walk_frames / idle_frame / fidget: which frames to use for moving, resting and shuffling
PROFILES = {
    "balloon": {"floating": True, "frame_ms": 380, "hover": 3, "bob": 3},
    # Kitty's first frame is the grounded pose, the other three are in flight.
    "kitty": {"flying": True, "walk_frames": [1, 2, 3], "fidget": False, "hover": 2, "bob": 1},
    # Hermit's last frame pulls into the shell: a resting-only trick, not part of the walk.
    "hermit": {"walk_frames": [0, 1, 2], "fidget_frames": [3] * 7},
    # Beetle's second frame has its eyes shut: a blink, only while standing and a quick one.
    "beetle": {"walk_frames": [0, 2, 3], "fidget_frames": [1], "fidget_interval": (2.5, 6.0), "fidget_step": 0.16},
    # TV Bot is grey and white, so plain hearts in its colour would be dull. It gets glitchy
    # neon scanline hearts instead.
    "tv_bot": {"heart_style": "robot", "heart_color": (77, 242, 214)},
}


@dataclass
class Character:
    id: str
    name: str
    frames: list = field(default_factory=list)  # facing right
    frames_flipped: list = field(default_factory=list)  # facing left
    floating: bool = False
    flying: bool = False
    frame_ms: int = 140
    walk_frames: list = None
    idle_frame: int = 0
    fidget: bool = True
    fidget_frames: list = None  # frames shown, one per step, when it shuffles; default all frames
    fidget_interval: tuple = (5.0, 12.0)  # seconds between shuffles while standing
    fidget_step: float = 0.22  # seconds each shuffle frame is shown
    heart_style: str = "classic"  # "classic" or "robot"
    heart_color: tuple = None  # overrides the colour taken from the sprite
    main_color: QColor = None  # the character's dominant colour, used for its hearts
    hover: int = 0
    bob: int = 0


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
    char.main_color = QColor(*char.heart_color) if char.heart_color else _main_color(strip.copy(QRect(0, 0, w, h)))
    count = len(char.frames)
    # The sheet frames are not a seamless loop (the last one does not lead back into the first),
    # so cycles run there and back: 0 1 2 3 2 1, instead of snapping from 3 to 0.
    char.walk_frames = _there_and_back(char.walk_frames or list(range(count)))
    if char.fidget_frames is None:
        char.fidget_frames = list(range(1, count)) + list(range(count - 2, 0, -1))  # then back to idle
    return char


def _main_color(image):
    """The dominant body colour: the most common vivid colour, or the most common one that is not
    the dark outline when the character is mostly grey or white (TV Bot, Ghost)."""
    everything, vivid = Counter(), Counter()
    for y in range(image.height()):
        for x in range(image.width()):
            c = image.pixelColor(x, y)
            if c.alpha() < 128 or max(c.red(), c.green(), c.blue()) <= 70:
                continue
            rgb = (c.red(), c.green(), c.blue())
            everything[rgb] += 1
            if c.hsvSaturationF() > 0.4 and c.valueF() > 0.5:
                vivid[rgb] += 1
    pool = vivid if sum(vivid.values()) >= 0.12 * sum(everything.values()) else everything
    return QColor(*pool.most_common(1)[0][0])


def _there_and_back(frames):
    return list(frames) + list(frames[-2:0:-1])
