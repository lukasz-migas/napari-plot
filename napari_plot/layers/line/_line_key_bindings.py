"""Key bindings for the Line layer."""

from __future__ import annotations

from typing import Callable

from napari.layers.base._base_constants import Mode
from napari.layers.utils.layer_utils import (
    register_layer_action,
    register_layer_attr_action,
)

from napari_plot.layers.line.line import Line


def register_line_action(description: str, repeatable: bool = False) -> Callable[[Callable], Callable]:
    return register_layer_action(Line, description, repeatable)


def register_line_mode_action(description: str) -> Callable[[Callable], Callable]:
    return register_layer_attr_action(Line, description, "mode")


@register_line_mode_action("Transform")
def activate_line_transform_mode(layer: Line) -> None:
    layer.mode = Mode.TRANSFORM


@register_line_mode_action("Pan/zoom")
def activate_line_pan_zoom_mode(layer: Line) -> None:
    layer.mode = Mode.PAN_ZOOM


line_fun_to_mode = [
    (activate_line_pan_zoom_mode, Mode.PAN_ZOOM),
    (activate_line_transform_mode, Mode.TRANSFORM),
]
