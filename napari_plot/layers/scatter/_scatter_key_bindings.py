"""Key bindings for the Centroids layer."""

from __future__ import annotations

from typing import Callable

from napari.layers.base._base_constants import Mode
from napari.layers.utils.layer_utils import (
    register_layer_action,
    register_layer_attr_action,
)

from napari_plot.layers.scatter import Scatter


def register_scatter_action(
    description: str, repeatable: bool = False
) -> Callable[[Callable], Callable]:
    return register_layer_action(Scatter, description, repeatable)


def register_scatter_mode_action(description: str) -> Callable[[Callable], Callable]:
    return register_layer_attr_action(Scatter, description, "mode")


@register_scatter_mode_action("Transform")
def activate_scatter_transform_mode(layer: Scatter) -> None:
    layer.mode = Mode.TRANSFORM


@register_scatter_mode_action("Pan/zoom")
def activate_scatter_pan_zoom_mode(layer: Scatter) -> None:
    layer.mode = Mode.PAN_ZOOM


scatter_fun_to_mode = [
    (activate_scatter_pan_zoom_mode, Mode.PAN_ZOOM),
    (activate_scatter_transform_mode, Mode.TRANSFORM),
]
