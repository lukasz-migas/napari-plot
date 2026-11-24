"""Keyboard shortcuts"""

from collections.abc import Generator

from napari_plot.components.dragtool import DragMode
from napari_plot.components.viewer_model import ViewerModel


@ViewerModel.bind_key("Control-Backspace")
@ViewerModel.bind_key("Control-Delete")
def remove_selected(viewer):
    """Remove selected layers."""
    viewer.layers.remove_selected()


@ViewerModel.bind_key("Control-A")
def select_all(viewer):
    """Selected all layers."""
    viewer.layers.select_all()


@ViewerModel.bind_key("Control-Shift-Backspace")
@ViewerModel.bind_key("Control-Shift-Delete")
def remove_all_layers(viewer):
    """Remove all layers."""
    viewer.layers.select_all()
    viewer.layers.remove_selected()


@ViewerModel.bind_key("Up")
def select_layer_above(viewer):
    """Select layer above."""
    viewer.layers.select_next()


@ViewerModel.bind_key("Down")
def select_layer_below(viewer):
    """Select layer below."""
    viewer.layers.select_previous()


@ViewerModel.bind_key("Shift-Up")
def also_select_layer_above(viewer):
    """Also select layer above."""
    viewer.layers.select_next(shift=True)


@ViewerModel.bind_key("Shift-Down")
def also_select_layer_below(viewer):
    """Also select layer below."""
    viewer.layers.select_previous(shift=True)


@ViewerModel.bind_key("Control-R")
def reset_view(viewer):
    """Reset view to original state."""
    viewer.reset_view()


@ViewerModel.bind_key("Control-G")
def toggle_grid(viewer: ViewerModel) -> Generator[None, None, None]:
    """Toggle plot grid visibility once per key press."""
    viewer.grid_lines.visible = not viewer.grid_lines.visible
    yield


@ViewerModel.bind_key("V")
def toggle_selected_visibility(viewer: ViewerModel) -> Generator[None, None, None]:
    """Toggle selected layer visibility once per key press."""
    viewer.layers.toggle_selected_visibility()
    yield


@ViewerModel.bind_key("Control-L")
def toggle_selected_editability(viewer: ViewerModel) -> Generator[None, None, None]:
    """Toggle selected layer editability once per key press."""
    viewer.layers.toggle_selected_editable()
    yield


@ViewerModel.bind_key("Home")
def reset_view_home(viewer: ViewerModel) -> None:
    """Reset view to original state."""
    viewer.reset_view()


def _bind_tool(key: str, mode: DragMode) -> None:
    """Bind ``key`` to switch the drag tool to ``mode``."""

    def activate_tool(viewer: ViewerModel) -> None:
        viewer.drag_tool.active = mode

    activate_tool.__doc__ = f"Use the {TOOL_SHORTCUTS_LABELS[mode]} tool."
    activate_tool.__name__ = f"activate_{mode.value}_tool"
    ViewerModel.bind_key(key, activate_tool)


# shortcuts of the drag tools; also shown in the tool menus
TOOL_SHORTCUTS: dict[DragMode, str] = {
    DragMode.AUTO: "A",
    DragMode.BOX: "Z",
    DragMode.VERTICAL_SPAN: "X",
    DragMode.HORIZONTAL_SPAN: "Y",
    DragMode.BOX_SELECT: "S",
    DragMode.LASSO: "L",
    DragMode.POLYGON: "P",
}
TOOL_SHORTCUTS_LABELS: dict[DragMode, str] = {
    DragMode.AUTO: "auto zoom",
    DragMode.BOX: "box zoom",
    DragMode.VERTICAL_SPAN: "x-range zoom",
    DragMode.HORIZONTAL_SPAN: "y-range zoom",
    DragMode.BOX_SELECT: "box select",
    DragMode.LASSO: "lasso select",
    DragMode.POLYGON: "polygon select",
}
for _mode, _key in TOOL_SHORTCUTS.items():
    _bind_tool(_key, _mode)


@ViewerModel.bind_key("C")
def toggle_crosshair(viewer: ViewerModel) -> Generator[None, None, None]:
    """Toggle the crosshair once per key press."""
    viewer.crosshair.visible = not viewer.crosshair.visible
    yield


@ViewerModel.bind_key("H")
def toggle_hover_readout(viewer: ViewerModel) -> Generator[None, None, None]:
    """Toggle the hover readout once per key press."""
    viewer.hover.visible = not viewer.hover.visible
    yield
