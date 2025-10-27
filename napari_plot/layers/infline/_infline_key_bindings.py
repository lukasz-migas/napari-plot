"""Add keybindings to the layer"""

from typing import Callable

from napari.layers.utils.layer_utils import (
    register_layer_action,
    register_layer_attr_action,
)

from napari_plot.layers.infline._infline_constants import Mode
from napari_plot.layers.infline.infline import InfLine


def register_infline_action(description: str, repeatable: bool = False) -> Callable[[Callable], Callable]:
    return register_layer_action(InfLine, description, repeatable)


def register_infline_mode_action(description: str) -> Callable[[Callable], Callable]:
    return register_layer_attr_action(InfLine, description, "mode")


@register_infline_mode_action("Add")
def activate_infline_add_mode(layer: InfLine) -> None:
    layer.mode = Mode.ADD


@register_infline_mode_action("Move")
def activate_infline_mode_mode(layer: InfLine) -> None:
    layer.mode = Mode.MOVE


@register_infline_mode_action("Select")
def activate_infline_select_mode(layer: InfLine) -> None:
    layer.mode = Mode.SELECT


@register_infline_mode_action("Transform")
def activate_infline_transform_mode(layer: InfLine) -> None:
    layer.mode = Mode.TRANSFORM


@register_infline_mode_action("Pan/zoom")
def activate_infline_pan_zoom_mode(layer: InfLine) -> None:
    layer.mode = Mode.PAN_ZOOM


@InfLine.bind_key("Backspace")
def activate_remove_mode(layer):
    layer.remove_selected()


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


infline_fun_to_mode = []
