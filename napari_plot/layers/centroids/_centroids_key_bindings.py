"""Key bindings for the Centroids layer."""

from __future__ import annotations

from typing import Callable

from napari.layers.base._base_constants import Mode
from napari.layers.utils.layer_utils import (
    register_layer_action,
    register_layer_attr_action,
)

from napari_plot.layers.centroids.centroids import Centroids


def register_centroids_action(
    description: str, repeatable: bool = False
) -> Callable[[Callable], Callable]:
    return register_layer_action(Centroids, description, repeatable)


def register_centroids_mode_action(description: str) -> Callable[[Callable], Callable]:
    return register_layer_attr_action(Centroids, description, "mode")


@register_centroids_mode_action("Transform")
def activate_centroids_transform_mode(layer: Centroids) -> None:
    layer.mode = Mode.TRANSFORM


@register_centroids_mode_action("Pan/zoom")
def activate_centroids_pan_zoom_mode(layer: Centroids) -> None:
    layer.mode = Mode.PAN_ZOOM


centroids_fun_to_mode = [
    (activate_centroids_pan_zoom_mode, Mode.PAN_ZOOM),
    (activate_centroids_transform_mode, Mode.TRANSFORM),
]
