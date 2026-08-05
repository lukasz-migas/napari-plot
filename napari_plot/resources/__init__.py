"""Get all paths."""

from __future__ import annotations

from pathlib import Path

from napari._qt.qt_resources import STYLES as STYLES_
from napari.resources._icons import ICONS as ICONS_
from qtextra.assets import get_stylesheet, update_icon_mapping, update_icons, update_styles

__all__ = ["get_stylesheet", "load_assets"]

ICON_PATH = (Path(__file__).parent / "icons").resolve()
ICONS = {x.stem: str(x) for x in ICON_PATH.iterdir() if x.suffix == ".svg"}
STYLE_PATH = (Path(__file__).parent / "qss").resolve()
STYLES = {f"{x.stem}-napari-plot": str(x) for x in STYLE_PATH.iterdir() if x.suffix == ".qss"}
ICON_MAPPING = {
    "axes": "mdi6.axis-arrow",
    "move": "fa5s.arrows-alt",
    "new_line": "msc.pulse",
    "new_centroids": "ri.bar-chart-fill",
    "new_inf_line": "mdi.infinity",
    "new_region": "ri.bar-chart-horizontal-fill",
    "new_points": "mdi.scatter-plot",
    "new_shapes": "fa5s.shapes",
    "zoom": "fa5s.search",
    "pan": "ph.hand-pointing",
    "select_empty": "|ph.navigation-arrow-bold",
    "select": "ph.navigation-arrow-fill",
    "select_points": "ph.navigation-arrow-fill",
    "select_points_empty": "ph.navigation-arrow-bold",
    "draw": "mdi.draw",
    "grid": "mdi.grid",
    "tool": "fa5s.tools",
    "tools": "fa5s.tools",
    "layers": "fa5s.layer-group",
    "vertical": "mdi.drag-vertical-variant",
    "horizontal": "mdi.drag-horizontal-variant",
    "close": "fa5s.times",
}
def load_assets() -> None:
    """Idempotently register napari-plot icons and styles with qtextra."""
    update_icons(ICONS_)
    update_icons(ICONS)
    STYLES_.update(STYLES)
    update_styles(STYLES_)
    update_icon_mapping(ICON_MAPPING)


load_assets()
