"""Get all paths."""

from __future__ import annotations

from pathlib import Path

from napari._qt.qt_resources import STYLES as STYLES_
from napari.resources._icons import ICONS as ICONS_
from qtextra.assets import get_stylesheet, update_icon_mapping, update_icons, update_styles

__all__ = ["get_stylesheet", "load_assets"]

ICON_PATH = (Path(__file__).parent / "icons").resolve()
ICONS = {x.stem: str(x) for x in ICON_PATH.iterdir() if x.suffix == ".svg"}
update_icons(ICONS_)
update_icons(ICONS)

STYLE_PATH = (Path(__file__).parent / "qss").resolve()
STYLES_.update({x.stem: str(x) for x in STYLE_PATH.iterdir() if x.suffix == ".qss"})
update_styles(STYLES_)

update_icon_mapping(
    {
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
        "tools": "fa5s.tools",
        "vertical": "mdi.drag-vertical-variant",
        "horizontal": "mdi.drag-horizontal-variant",
        "close": "fa5s.times",
    },
)


def load_assets() -> None:
    """No-op function that ensures icons and styles are loaded properly."""
