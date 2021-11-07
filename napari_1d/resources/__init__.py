"""Get all paths."""
from pathlib import Path

ICON_PATH = (Path(__file__).parent / "icons").resolve()
ICONS = {x.stem: str(x) for x in ICON_PATH.iterdir() if x.suffix == ".svg"}


QTA_MAPPING = {
    "layers": "fa5s.layer-group",
    "clipboard": "fa5s.clipboard-list",
    "axes": "mdi6.axis-arrow",
    "text": "mdi.format-text",
    "grid": "mdi.grid",
    "erase": "ph.eraser-fill",
    "zoom_out": "fa5s.expand",
    "target": "mdi6.target",
    "move": "ei.move",
    "add": "ri.add-circle-fill",
    "minimise": "fa5s.window-minimize",
    "new_line": "msc.pulse",
    "new_centroids": "ri.bar-chart-fill",
    "new_inf_line": "mdi.infinity",
    "new_region": "ri.bar-chart-horizontal-fill",
    "new_shapes": "mdi.triangle",
    "new_points": "mdi6.scatter-plot",
    "home": "fa5s.home",
    "zoom": "fa5s.search",
    "pan_zoom": "fa5s.search",
    "select": "fa5s.location-arrow",
    "select_points": "fa5s.location-arrow",
    "delete_shape": "fa5s.times",
    "move_back": "mdi6.arrange-send-backward",
    "move_front": "mdi6.arrange-bring-to-front",
}
