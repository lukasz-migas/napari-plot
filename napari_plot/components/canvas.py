"""Canvas models for plot-specific grid placement."""

from __future__ import annotations

from math import ceil, sqrt
from typing import TYPE_CHECKING

from napari.components.canvas import Canvas
from napari.components.grid import GridCanvas
from pydantic import Field

from napari_plot.layers._grouping import get_layer_group

if TYPE_CHECKING:
    from collections.abc import Sequence

    from napari.layers import Layer


class PlotGridCanvas(GridCanvas):
    """Grid model with optional placement by layer metadata."""

    group_by_metadata: bool = False

    def _metadata_groups(self, layers: Sequence[Layer]) -> tuple[dict[int, int], list[int]] | None:
        if not self.enabled or not self.group_by_metadata:
            return None
        groups = [get_layer_group(layer) for layer in layers]
        if not any(layer.visible and group is not None for layer, group in zip(layers, groups, strict=True)):
            return None
        group_of: dict[int, int] = {}
        first: dict[str, int] = {}
        for index, group in enumerate(groups):
            group_of[index] = first.setdefault(group, index) if group is not None else index
        occupied = sorted({group_of[i] for i, layer in enumerate(layers) if layer.visible})
        return group_of, occupied

    def _viewbox_groups(self, layers: Sequence[Layer]) -> tuple[dict[int, int], list[int]]:
        return self._metadata_groups(layers) or super()._viewbox_groups(layers)

    def actual_shape(self, layers: Sequence[Layer]) -> tuple[int, int]:
        """Return the effective shape, using automatic dimensions for metadata groups."""
        groups = self._metadata_groups(layers)
        if groups is None:
            return super().actual_shape(layers)
        count = len(groups[1])
        cols = ceil(sqrt(count))
        return ceil(count / cols), cols


class PlotCanvas(Canvas):
    """Canvas model with plot grid controls."""

    grid: PlotGridCanvas = Field(default_factory=PlotGridCanvas, frozen=True)
