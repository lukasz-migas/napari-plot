"""Group membership shared by native and custom layers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from napari.layers import Layer


LAYER_GROUP_KEY = "napari_plot.group"


def get_layer_group(layer: Layer) -> str | None:
    """Return the layer's group ID, if present."""
    group = layer.metadata.get(LAYER_GROUP_KEY)
    return group if isinstance(group, str) else None
