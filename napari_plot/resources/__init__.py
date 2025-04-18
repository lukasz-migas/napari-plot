"""Get all paths."""

from __future__ import annotations

from pathlib import Path

from napari._qt.qt_resources import STYLES as STYLES_
from napari.resources._icons import ICONS as ICONS_
from qtextra.assets import STYLES, get_stylesheet, update_icons, update_styles

ICON_PATH = (Path(__file__).parent / "icons").resolve()
ICONS = {x.stem: str(x) for x in ICON_PATH.iterdir() if x.suffix == ".svg"}
ICONS_.update(ICONS)

STYLE_PATH = (Path(__file__).parent / "qss").resolve()
STYLES_.update({x.stem: str(x) for x in STYLE_PATH.iterdir() if x.suffix == ".qss"})

update_styles(STYLES_)
update_icons(
    {
        "delete": "fa5s.trash",
        "layers": "fa5s.layer-group",
        "ipython": "fa5s.terminal",
        "clipboard": "fa5s.clipboard-list",
        "axes": "mdi6.axis-arrow",
        "text": "mdi.format-text",
        "grid": "mdi.grid",
        "erase": "ph.eraser-fill",
        "zoom_out": "fa5s.expand",
        "target": "mdi6.target",
        "move": "fa5s.arrows-alt",
        # "add": "ri.add-circle-fill",
        "add": "ri.add-circle-line",
        "minimise": "fa5s.window-minimize",
        "new_line": "msc.pulse",
        "new_centroids": "ri.bar-chart-fill",
        "new_inf_line": "mdi.infinity",
        "new_region": "ri.bar-chart-horizontal-fill",
        "new_shapes": "mdi.triangle",
        "new_points": "mdi6.scatter-plot",
        "home": "fa5s.home",
        "zoom": "fa5s.search",
        "pan": "ph.hand-pointing",
        # "transform": "mdi.arrow-expand-all",
        # "transform": "mdi.select-drag",
        "transform": "ph.selection-plus-fill",
        # "pan_zoom": "ei.move",
        "pan_zoom": "fa5s.arrows-alt",
        # "select": "fa5s.location-arrow",
        "select_empty": "|ph.navigation-arrow-bold",
        "select": "ph.navigation-arrow-fill",
        # "select_points": "fa5s.location-arrow",
        "select_points": "ph.navigation-arrow-fill",
        "select_points_empty": "|ph.navigation-arrow-bold",
        "delete_shape": "fa5s.times",
        "move_back": "mdi6.arrange-send-backward",
        "move_front": "mdi6.arrange-bring-to-front",
        "draw": "mdi.draw",
        "tools": "fa5s.tools",
        "vertical": "mdi.drag-vertical-variant",
        "horizontal": "mdi.drag-horizontal-variant",
        "close": "fa5s.times",
    }
)
