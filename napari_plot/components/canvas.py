"""Canvas models for plot-specific grid placement."""

from __future__ import annotations

from itertools import product
from math import ceil, isfinite, sqrt
from typing import TYPE_CHECKING, Literal

from napari.components.canvas import Canvas
from napari.components.grid import GridCanvas
from napari.utils.events import Event, EventedModel
from pydantic import Field, field_validator

from napari_plot.components.axis import Axis, AxisScale
from napari_plot.components.joint_grid import JointPanel, joint_panel
from napari_plot.layers._grouping import get_layer_group

if TYPE_CHECKING:
    from collections.abc import Sequence

    from napari.layers import Layer


class PlotGridCell(EventedModel):
    """Optional axis settings for one (row, column) in the plot grid.

    ``None`` inherits the viewer setting. Limits apply when the corresponding axis is independent. A ``group``
    reserves this position for layers with that metadata group.
    """

    row: int = Field(ge=0, frozen=True)
    column: int = Field(ge=0, frozen=True)
    group: str | None = None
    x_label: str | None = None
    y_label: str | None = None
    x_scale: AxisScale | None = None
    y_scale: AxisScale | None = None
    x_categories: tuple[str, ...] | None = None
    y_categories: tuple[str, ...] | None = None
    xlim: tuple[float, float] | None = None
    ylim: tuple[float, float] | None = None

    @field_validator("xlim", "ylim")
    @classmethod
    def _validate_limits(cls, value: tuple[float, float] | None) -> tuple[float, float] | None:
        if value is not None and (value[0] == value[1] or not all(map(isfinite, value))):
            raise ValueError("Cell axis limits must be two distinct finite values.")
        return value

    def axis_scale(self, name: Literal["x", "y"], axis: Axis) -> AxisScale:
        """Return the effective scale for an axis in this cell."""
        if getattr(self, f"{name}_categories") is not None:
            return AxisScale.CATEGORICAL
        return getattr(self, f"{name}_scale") or getattr(axis, f"{name}_scale")


class PlotGridCanvas(GridCanvas):
    """Grid model with optional placement by layer metadata."""

    group_by_metadata: bool = False
    sharex: bool = True
    sharey: bool = True
    cells: tuple[PlotGridCell, ...] = ()
    joint: bool = False
    joint_top: bool = True
    joint_right: bool = True
    joint_ratio: float = Field(default=5, gt=0, allow_inf_nan=False)
    joint_top_label: str = ""
    joint_right_label: str = ""
    joint_hidden_labels: tuple[JointPanel, ...] = ()

    def __init__(self, **data: object) -> None:
        super().__init__(**data)
        self.events.add(cell_changed=Event)
        self.events.cells.connect(self._connect_cells)
        self._connect_cells()

    def _connect_cells(self, _event: Event | None = None) -> None:
        for cell in self.cells:
            cell.events.connect(self._on_cell_changed)

    def _on_cell_changed(self, event: Event) -> None:
        if any(event.source is cell for cell in self.cells):
            self.events.cell_changed(cell=event.source, field=event.type)

    def cell(self, row: int, column: int) -> PlotGridCell:
        """Get or create axis settings for the given zero-based grid position."""
        existing = self._find_cell(row, column)
        if existing is not None:
            return existing
        cell = PlotGridCell(row=row, column=column)
        self.cells = (*self.cells, cell)
        return cell

    def _find_cell(self, row: int, column: int) -> PlotGridCell | None:
        return next((cell for cell in self.cells if (cell.row, cell.column) == (row, column)), None)

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
        if self.enabled and self.joint:
            return (2 if self.joint_top else 1, 2 if self.joint_right else 1)
        assigned = (
            [cell for cell in self.cells if cell.group is not None] if self.enabled and self.group_by_metadata else []
        )
        if assigned:
            rows, cols = self.shape
            return max(rows, 1 + max(cell.row for cell in assigned)), max(
                cols, 1 + max(cell.column for cell in assigned)
            )
        groups = self._metadata_groups(layers)
        if groups is None:
            return super().actual_shape(layers)
        count = len(groups[1])
        rows, cols = self.shape
        if rows == cols == -1 or (rows > 0 and cols > 0 and rows * cols < count):
            cols = ceil(sqrt(count))
            return ceil(count / cols), cols
        if cols == -1:
            cols = ceil(count / rows)
        if rows == -1:
            rows = ceil(count / cols)
        return rows, cols

    def _positions(self, layers: Sequence[Layer]) -> list[tuple[int, int]]:
        if self.enabled and self.joint:
            main_row = int(self.joint_top)
            positions = {"joint": (main_row, 0), "top": (0, 0), "right": (main_row, 1)}
            return [
                positions[joint_panel(layer, top=self.joint_top, right=self.joint_right)] if layer.visible else (-1, -1)
                for layer in layers
            ]
        assignments = (
            {cell.group: (cell.row, cell.column) for cell in self.cells if cell.group is not None}
            if self.enabled and self.group_by_metadata
            else {}
        )
        if not assignments:
            return super()._positions(layers)
        rows, cols = self.actual_shape(layers)
        reserved = set(assignments.values())
        free = iter(position for position in product(range(rows), range(cols)) if position not in reserved)
        visible = set(self._effective_indices(layers))
        group_of, _ = self._viewbox_groups(layers)
        unassigned: dict[int, tuple[int, int]] = {}
        positions = []
        for index, layer in enumerate(layers):
            position = (-1, -1)
            if index in visible:
                group = get_layer_group(layer)
                if group in assignments:
                    position = assignments[group]
                else:
                    native_group = group_of[index]
                    if native_group not in unassigned:
                        unassigned[native_group] = next(free, (rows - 1, cols - 1))
                    position = unassigned[native_group]
            positions.append(position)
        return positions


class PlotCanvas(Canvas):
    """Canvas model with plot grid controls."""

    grid: PlotGridCanvas = Field(default_factory=PlotGridCanvas, frozen=True)
