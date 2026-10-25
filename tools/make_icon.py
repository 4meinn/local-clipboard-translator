"""Build assets/icon.ico (exe, installer, tray, windows) from assets/logo_pixel.png.

    python tools/make_icon.py

logo_pixel.png is the logo at its true size (22x23 pixels). It is enlarged by whole-number
factors so the pixel edges stay sharp; only the 16 px size has to be averaged down.
assets/logo.png is the same artwork enlarged to 1024 px for the README.
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
LOGO = ROOT / "assets" / "logo_pixel.png"
ICON = ROOT / "assets" / "icon.ico"
SIZES = [16, 24, 32, 48, 64, 128, 256]


def render(pix, size):
    margin = 0 if size <= 32 else size // 32
    room = size - 2 * margin
    k = room // max(pix.size)
    if k >= 1:
        art = pix.resize((pix.width * k, pix.height * k), Image.NEAREST)
    else:  # smaller than the artwork itself: average it down
        scale = room / max(pix.size)
        art = pix.resize((max(1, round(pix.width * scale)), max(1, round(pix.height * scale))), Image.LANCZOS)
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    icon.paste(art, ((size - art.width) // 2, (size - art.height) // 2), art)
    return icon


def main():
    pix = Image.open(LOGO).convert("RGBA")
    frames = [render(pix, s) for s in SIZES]
    frames[-1].save(ICON, sizes=[(s, s) for s in SIZES], append_images=frames[:-1])
    print("wrote", ICON)


if __name__ == "__main__":
    main()
