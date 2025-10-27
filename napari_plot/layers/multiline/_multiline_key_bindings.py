"""Key bindings for the MultiLine layer."""

from __future__ import annotations

from typing import Callable

from napari.layers.base._base_constants import Mode
from napari.layers.utils.layer_utils import register_layer_action, register_layer_attr_action

from napari_plot.layers.multiline import MultiLine


def register_multiline_action(description: str, repeatable: bool = False) -> Callable[[Callable], Callable]:
    return register_layer_action(MultiLine, description, repeatable)


def register_multiline_mode_action(description: str) -> Callable[[Callable], Callable]:
    return register_layer_attr_action(MultiLine, description, "mode")


@register_multiline_mode_action("Transform")
def activate_multiline_transform_mode(layer: MultiLine) -> None:
    layer.mode = Mode.TRANSFORM


@register_multiline_mode_action("Pan/zoom")
def activate_multiline_pan_zoom_mode(layer: MultiLine) -> None:
    layer.mode = Mode.PAN_ZOOM


multiline_fun_to_mode = [
    (activate_multiline_pan_zoom_mode, Mode.PAN_ZOOM),
    (activate_multiline_transform_mode, Mode.TRANSFORM),
]
