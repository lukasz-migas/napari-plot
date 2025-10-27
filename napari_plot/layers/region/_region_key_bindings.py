"""Add keybindings to the layer"""

from typing import Callable

from app_model.types import KeyCode
from napari.layers.utils.layer_utils import register_layer_action, register_layer_attr_action

from napari_plot.layers.region._region_constants import Mode
from napari_plot.layers.region.region import Region


def register_region_action(description: str, repeatable: bool = False) -> Callable[[Callable], Callable]:
    return register_layer_action(Region, description, repeatable)


def register_region_mode_action(description: str) -> Callable[[Callable], Callable]:
    return register_layer_attr_action(Region, description, "mode")


@register_region_mode_action("Add")
def activate_region_add_mode(layer: Region) -> None:
    layer.mode = Mode.ADD


@register_region_mode_action("Move")
def activate_region_move_mode(layer: Region) -> None:
    layer.mode = Mode.MOVE


@register_region_mode_action("Select")
def activate_region_select_mode(layer: Region) -> None:
    layer.mode = Mode.SELECT


@register_region_mode_action("Edit")
def activate_region_edit_mode(layer: Region) -> None:
    layer.mode = Mode.EDIT


@register_region_mode_action("Transform")
def activate_region_transform_mode(layer: Region) -> None:
    layer.mode = Mode.TRANSFORM


@register_region_mode_action("Pan/zoom")
def activate_region_pan_zoom_mode(layer: Region) -> None:
    layer.mode = Mode.PAN_ZOOM


region_fun_to_mode = [
    (activate_region_add_mode, Mode.ADD),
    (activate_region_move_mode, Mode.MOVE),
    (activate_region_select_mode, Mode.SELECT),
    (activate_region_edit_mode, Mode.EDIT),
    (activate_region_pan_zoom_mode, Mode.PAN_ZOOM),
    (activate_region_transform_mode, Mode.TRANSFORM),
]


@Region.bind_key(KeyCode.Space, overwrite=True)
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


@register_region_action("Delete any selected shapes")
def delete_selected_region(layer: Region) -> None:
    """Delete any selected shapes."""
    layer.remove_selected()


@register_region_action("Move to front")
def move_region_selection_to_front(layer: Region) -> None:
    layer.move_to_front()


@register_region_action("Move to back")
def move_region_selection_to_back(layer: Region) -> None:
    layer.move_to_back()


@Region.bind_key(KeyCode.Enter, overwrite=True)
def accept_current(layer):
    """Accept current selection."""
    layer.accept()
