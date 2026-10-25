import sys
from pathlib import Path


def asset_path(*parts):
    """Resolve a bundled asset both from the source tree and from a PyInstaller build."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parents[2]
    return base.joinpath("assets", *parts)
