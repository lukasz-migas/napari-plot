"""Keyboard shortcuts"""
from .viewer_model import ViewerModel


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
def toggle_grid(viewer):
    """Toggle grid mode."""
    viewer.grid.enabled = not viewer.grid.enabled


@ViewerModel.bind_key("V")
def toggle_selected_visibility(viewer):
    """Toggle visibility of selected layers"""
    viewer.layers.toggle_selected_visibility()


@ViewerModel.bind_key("Control-L")
def toggle_selected_editability(viewer):
    """Toggle visibility of selected layers"""
    viewer.layers.toggle_selected_editable()
