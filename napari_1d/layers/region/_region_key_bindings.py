"""Add keybindings to the layer"""
from ._region_constants import Mode
from .region import Region


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


@Region.bind_key("S")
def activate_select_mode(layer):
    """Activate move tool."""
    layer.mode = Mode.SELECT


@Region.bind_key("Z")
@Region.bind_key("Escape")
def activate_pan_zoom_mode(layer):
    """Activate pan and zoom mode."""
    layer.mode = Mode.PAN_ZOOM


@Region.bind_key("Enter")
def accept_current(layer):
    """Accept current selection."""
    layer.accept()
