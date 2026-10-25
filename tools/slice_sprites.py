"""Slice assets/source/TL_Creatures.png into one transparent strip per character.

The source sheet is RGB with a two-colour checkerboard background, 32x32 cells,
5 columns starting at (64, 32), one character per row (only the first 4 are used). Run from the repo root:

    python tools/slice_sprites.py
"""
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SHEET = ROOT / "assets" / "source" / "TL_Creatures.png"
OUT = ROOT / "assets" / "characters"

CELL = 32
ORIGIN = (64, 32)
COLUMNS = 4  # the sheet has 5; the fifth is a "hurt" frame that breaks the walk cycle
BACKGROUNDS = {(157, 142, 135), (145, 112, 92)}

CHARACTERS = [
    ("berry", "Berry"),
    ("hermit", "Hermit"),
    ("balloon", "Balloon"),
    ("sprout_bot", "Sprout Bot"),
    ("blob", "Blob"),
    ("kitty", "Kitty"),
    ("beetle", "Beetle"),
    ("tv_bot", "TV Bot"),
    ("ghost", "Ghost"),
]


def cut_cell(sheet, col, row):
    x0 = ORIGIN[0] + col * CELL
    y0 = ORIGIN[1] + row * CELL
    cell = sheet.crop((x0, y0, x0 + CELL, y0 + CELL)).convert("RGBA")
    px = cell.load()
    for y in range(CELL):
        for x in range(CELL):
            if px[x, y][:3] in BACKGROUNDS:
                px[x, y] = (0, 0, 0, 0)
    return cell


def main():
    sheet = Image.open(SHEET).convert("RGB")
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for row, (cid, name) in enumerate(CHARACTERS):
        cells = [cut_cell(sheet, col, row) for col in range(COLUMNS)]
        cells = [c for c in cells if c.getbbox()]
        left = min(c.getbbox()[0] for c in cells)
        top = min(c.getbbox()[1] for c in cells)
        right = max(c.getbbox()[2] for c in cells)
        bottom = max(c.getbbox()[3] for c in cells)
        w, h = right - left, bottom - top
        strip = Image.new("RGBA", (w * len(cells), h), (0, 0, 0, 0))
        for i, c in enumerate(cells):
            strip.paste(c.crop((left, top, right, bottom)), (i * w, 0))
        strip.save(OUT / f"{cid}.png")
        manifest.append({"id": cid, "name": name, "frames": len(cells), "frame_width": w, "frame_height": h})
        print(f"{cid}: {len(cells)} frames of {w}x{h}")
    (OUT / "characters.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
