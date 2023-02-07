"""Add keybindings to the layer"""
from napari_plot.layers.region._region_constants import Mode
from napari_plot.layers.region.region import Region


@Region.bind_key("Space")
def hold_to_pan_zoom(layer):
    """Hold to pan and zoom in the viewer."""
    if layer._mode != Mode.PAN_ZOOM:
        # on key press
        prev_mode = layer.mode
        layer.mode = Mode.PAN_ZOOM

        yield

        # on key release
        layer.mode = prev_mode
        layer._set_highlight()


@Region.bind_key("M")
def activate_move_mode(layer):
    """Activate move tool."""
    layer.mode = Mode.MOVE


@Region.bind_key("A")
def activate_add_mode(layer):
    """Activate move tool."""
    layer.mode = Mode.ADD


@Region.bind_key("S")
def activate_select_mode(layer):
    """Activate move tool."""
    layer.mode = Mode.SELECT


@Region.bind_key("E")
def activate_edit_mode(layer):
    """Activate move tool."""
    layer.mode = Mode.EDIT


@Region.bind_key("Z")
@Region.bind_key("Escape")
def activate_pan_zoom_mode(layer):
    """Activate pan and zoom mode."""
    layer.mode = Mode.PAN_ZOOM


@Region.bind_key("Backspace")
@Region.bind_key("Delete")
def delete_current(layer):
    """Activate pan and zoom mode."""
    layer.remove_selected()


@Region.bind_key("Enter")
def accept_current(layer):
    """Accept current selection."""
    layer.accept()
