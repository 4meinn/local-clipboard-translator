"""Build assets/icon.ico (used by the exe and the installer) from a character sprite.

    python tools/make_icon.py [character_id]
"""
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CHARACTERS = ROOT / "assets" / "characters"
SIZES = [16, 24, 32, 48, 64, 128, 256]


def main():
    char_id = sys.argv[1] if len(sys.argv) > 1 else "berry"
    manifest = json.loads((CHARACTERS / "characters.json").read_text("utf-8"))
    entry = next(e for e in manifest if e["id"] == char_id)
    w, h = entry["frame_width"], entry["frame_height"]
    sprite = Image.open(CHARACTERS / f"{char_id}.png").convert("RGBA").crop((0, 0, w, h))

    side = max(w, h) + 4
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(sprite, ((side - w) // 2, side - h - 2))
    scale = 256 // side
    big = canvas.resize((side * scale, side * scale), Image.NEAREST)
    icon = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    icon.paste(big, ((256 - big.width) // 2, (256 - big.height) // 2))
    icon.save(ROOT / "assets" / "icon.ico", sizes=[(s, s) for s in SIZES])


if __name__ == "__main__":
    main()
