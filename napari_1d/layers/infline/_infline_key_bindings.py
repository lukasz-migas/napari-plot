"""Add keybindings to the layer"""
from ._infline_constants import Mode
from .infline import InfLine


@InfLine.bind_key("Space")
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


@InfLine.bind_key("M")
def activate_move_mode(layer):
    """Activate move tool."""
    layer.mode = Mode.MOVE


@InfLine.bind_key("Z")
@InfLine.bind_key("Escape")
def activate_pan_zoom_mode(layer):
    """Activate pan and zoom mode."""
    layer.mode = Mode.PAN_ZOOM
