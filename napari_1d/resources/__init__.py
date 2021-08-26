"""Get all paths."""
from pathlib import Path

ICON_PATH = (Path(__file__).parent / "icons").resolve()
ICONS = {x.stem: str(x) for x in ICON_PATH.iterdir() if x.suffix == ".svg"}
