"""Finite horizontal and vertical bar layer."""

from __future__ import annotations

import typing as ty
from enum import StrEnum

import numpy as np
from napari.layers.base import ActionType
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import Event

from napari_plot.layers.base import BaseLayer


class BarOrientation(StrEnum):
    """Supported bar directions."""

    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"


def _coerce_bar_data(data: ty.Any) -> np.ndarray:
    """Normalize bar values to ``(position, value)`` rows."""
    if data is None:
        return np.empty((0, 2), dtype=float)
    array = np.asarray(data, dtype=float)
    if array.ndim == 1:
        return np.column_stack((np.arange(len(array), dtype=float), array))
    if array.ndim != 2 or array.shape[1] != 2:
        raise ValueError("Bar data must be a 1D value array or an (N, 2) position/value array.")
    return array


def _coerce_colors(value: ty.Any, count: int, name: str) -> np.ndarray:
    """Normalize one or many colors to one RGBA row per bar."""
    if count == 0:
        return np.empty((0, 4), dtype=float)
    colors = transform_color(value)
    if len(colors) == 1:
        return np.broadcast_to(colors, (count, 4)).copy()
    if len(colors) != count:
        raise ValueError(f"{name} must contain one color or one color per bar.")
    return np.asarray(colors, dtype=float)


class Bar(BaseLayer):
    """Layer rendering finite horizontal or vertical bars.

    Parameters
    ----------
    data : array-like
        Either one value per bar or ``(position, value)`` rows.
    orientation : str or BarOrientation
        Whether values extend vertically or horizontally from ``baseline``.
    baseline : float
        Shared value from which every bar begins.
    width : float
        Bar width in data coordinates.
    fill_color : color or sequence of colors
        Fill color shared by all bars or supplied per bar.
    border_color : color or sequence of colors
        Border color shared by all bars or supplied per bar.
    border_width : float
        Border width in screen pixels.
    """

    _highlight_color = np.asarray((0.0, 0.6, 1.0, 0.85))

    def __init__(
        self,
        data=None,
        *,
        orientation: str | BarOrientation = BarOrientation.VERTICAL,
        baseline: float = 0.0,
        width: float = 0.8,
        fill_color: ty.Any = "white",
        border_color: ty.Any = "dimgray",
        border_width: float = 1.0,
        axis_labels=None,
        name=None,
        metadata=None,
        scale=None,
        translate=None,
        rotate=None,
        shear=None,
        affine=None,
        opacity=1.0,
        blending="translucent",
        experimental_clipping_planes=None,
        projection_mode="none",
        units=None,
        visible=True,
    ) -> None:
        data = _coerce_bar_data(data)
        if width <= 0:
            raise ValueError("Bar width must be positive.")
        if border_width < 0:
            raise ValueError("Bar border width cannot be negative.")
        super().__init__(
            data,
            axis_labels=axis_labels,
            name=name,
            metadata=metadata,
            scale=scale,
            translate=translate,
            rotate=rotate,
            shear=shear,
            affine=affine,
            opacity=opacity,
            blending=blending,
            experimental_clipping_planes=experimental_clipping_planes,
            projection_mode=projection_mode,
            units=units,
            visible=visible,
        )
        self.events.add(
            orientation=Event,
            baseline=Event,
            width=Event,
            fill_color=Event,
            border_color=Event,
            border_width=Event,
            highlight=Event,
        )
        self._data = data
        self._orientation = BarOrientation(orientation)
        self._baseline = float(baseline)
        self._width = float(width)
        self._fill_color = _coerce_colors(fill_color, len(data), "fill_color")
        self._border_color = _coerce_colors(border_color, len(data), "border_color")
        self._border_width = float(border_width)
        self._selected_data: set[int] = set()
        self.mouse_drag_callbacks.append(_select_bar)

    def _get_state(self) -> dict[str, ty.Any]:
        """Return serializable state used by duplication and layer actions."""
        state = self._get_base_state()
        state.update(
            data=self.data,
            orientation=self.orientation,
            baseline=self.baseline,
            width=self.width,
            fill_color=self.fill_color,
            border_color=self.border_color,
            border_width=self.border_width,
        )
        return state

    @property
    def data(self) -> np.ndarray:
        """Bar ``(position, value)`` rows."""
        return self._data

    @data.setter
    def data(self, value: ty.Any) -> None:
        data = _coerce_bar_data(value)
        old_count = len(self._data)
        self._data = data
        if hasattr(self, "_fill_color") and len(data) != old_count:
            fill = self._fill_color[0] if old_count else "white"
            border = self._border_color[0] if old_count else "dimgray"
            self._fill_color = _coerce_colors(fill, len(data), "fill_color")
            self._border_color = _coerce_colors(border, len(data), "border_color")
            self.selected_data = {index for index in self.selected_data if index < len(data)}
        self._emit_new_data(action_type=ActionType.CHANGED)

    @property
    def positions(self) -> np.ndarray:
        """Bar center positions."""
        return self.data[:, 0]

    @property
    def values(self) -> np.ndarray:
        """Bar endpoint values."""
        return self.data[:, 1]

    @property
    def orientation(self) -> BarOrientation:
        """Direction in which bars extend from the baseline."""
        return self._orientation

    @orientation.setter
    def orientation(self, value: str | BarOrientation) -> None:
        self._orientation = BarOrientation(value)
        self.events.orientation()
        self.events.set_data()

    @property
    def baseline(self) -> float:
        """Shared start value for all bars."""
        return self._baseline

    @baseline.setter
    def baseline(self, value: float) -> None:
        self._baseline = float(value)
        self.events.baseline()
        self.events.set_data()

    @property
    def width(self) -> float:
        """Bar width in data coordinates."""
        return self._width

    @width.setter
    def width(self, value: float) -> None:
        if value <= 0:
            raise ValueError("Bar width must be positive.")
        self._width = float(value)
        self.events.width()
        self.events.set_data()

    @property
    def fill_color(self) -> np.ndarray:
        """One RGBA fill color per bar."""
        return self._fill_color

    @fill_color.setter
    def fill_color(self, value: ty.Any) -> None:
        self._fill_color = _coerce_colors(value, len(self.data), "fill_color")
        self.events.fill_color()

    @property
    def color(self) -> np.ndarray:
        """Compatibility alias for the representative fill colors."""
        return self.fill_color

    @color.setter
    def color(self, value: ty.Any) -> None:
        self.fill_color = value

    @property
    def border_color(self) -> np.ndarray:
        """One RGBA border color per bar."""
        return self._border_color

    @border_color.setter
    def border_color(self, value: ty.Any) -> None:
        self._border_color = _coerce_colors(value, len(self.data), "border_color")
        self.events.border_color()

    @property
    def border_width(self) -> float:
        """Border width in screen pixels."""
        return self._border_width

    @border_width.setter
    def border_width(self, value: float) -> None:
        if value < 0:
            raise ValueError("Bar border width cannot be negative.")
        self._border_width = float(value)
        self.events.border_width()

    @property
    def selected_data(self) -> set[int]:
        """Indices of selected bars."""
        return self._selected_data

    @selected_data.setter
    def selected_data(self, value: ty.Iterable[int]) -> None:
        selected = {int(index) for index in value}
        if any(index < 0 or index >= len(self.data) for index in selected):
            raise IndexError("Selected bar index is outside the layer data.")
        self._selected_data = selected
        if hasattr(self, "events") and hasattr(self.events, "highlight"):
            self.events.highlight()

    def remove_selected(self) -> None:
        """Remove selected bars and their per-bar colors."""
        if not self.selected_data:
            return
        keep = np.ones(len(self.data), dtype=bool)
        keep[list(self.selected_data)] = False
        self._data = self.data[keep]
        self._fill_color = self.fill_color[keep]
        self._border_color = self.border_color[keep]
        self.selected_data = set()
        self._emit_new_data(action_type=ActionType.REMOVED)

    def _rectangle_vertices(self) -> np.ndarray:
        """Return four ``(x, y)`` vertices for each bar."""
        vertices = np.empty((len(self.data), 4, 2), dtype=float)
        position = self.positions
        value = self.values
        half_width = self.width / 2
        if self.orientation is BarOrientation.VERTICAL:
            vertices[:, :, 0] = np.column_stack(
                (position - half_width, position + half_width, position + half_width, position - half_width)
            )
            vertices[:, :, 1] = np.column_stack(
                (
                    np.full(len(value), self.baseline),
                    np.full(len(value), self.baseline),
                    value,
                    value,
                )
            )
        else:
            vertices[:, :, 0] = np.column_stack(
                (
                    np.full(len(value), self.baseline),
                    value,
                    value,
                    np.full(len(value), self.baseline),
                )
            )
            vertices[:, :, 1] = np.column_stack(
                (position - half_width, position - half_width, position + half_width, position + half_width)
            )
        return vertices

    def _mesh_data(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return flattened vertices, triangle faces, and vertex colors."""
        vertices = self._rectangle_vertices().reshape(-1, 2)
        base = np.arange(len(self.data), dtype=np.uint32)[:, None] * 4
        faces = (base + np.asarray((0, 1, 2, 0, 2, 3), dtype=np.uint32)).reshape(-1, 3)
        colors = self.fill_color.copy()
        if self.selected_data:
            colors[list(self.selected_data)] = self._highlight_color
        return vertices, faces, np.repeat(colors, 4, axis=0)

    def _border_data(self) -> tuple[np.ndarray, np.ndarray]:
        """Return line-segment vertices and matching colors for bar borders."""
        rectangles = self._rectangle_vertices()
        edges = rectangles[:, (0, 1, 1, 2, 2, 3, 3, 0), :].reshape(-1, 2)
        colors = self.border_color.copy()
        if self.selected_data:
            colors[list(self.selected_data)] = self._highlight_color
        return edges, np.repeat(colors, 8, axis=0)

    def _get_value(self, position) -> int | None:
        """Return the topmost bar at a data-space ``(y, x)`` position."""
        if len(self.data) == 0:
            return None
        point = np.asarray((position[1], position[0]))
        rectangles = self._rectangle_vertices()
        minimum = rectangles.min(axis=1)
        maximum = rectangles.max(axis=1)
        candidates = np.flatnonzero(np.all((point >= minimum) & (point <= maximum), axis=1))
        return int(candidates[-1]) if len(candidates) else None

    @property
    def _extent_data(self) -> np.ndarray:
        if len(self.data) == 0:
            return np.full((2, 2), np.nan)
        rectangles = self._rectangle_vertices().reshape(-1, 2)
        return np.vstack((rectangles.min(axis=0)[::-1], rectangles.max(axis=0)[::-1]))

    def _get_x_region_extent(
        self,
        x_min: float,
        x_max: float,
    ) -> tuple[float | None, float | None]:
        """Return the y extent of bars intersecting an x-axis interval."""
        if len(self.data) == 0:
            return None, None
        if self.orientation is BarOrientation.VERTICAL:
            mask = (self.positions + self.width / 2 >= x_min) & (self.positions - self.width / 2 <= x_max)
            values = self.values[mask]
            if len(values) == 0:
                return None, None
            return min(self.baseline, np.min(values)), max(self.baseline, np.max(values))

        value_min = np.minimum(self.baseline, self.values)
        value_max = np.maximum(self.baseline, self.values)
        mask = (value_max >= x_min) & (value_min <= x_max)
        positions = self.positions[mask]
        if len(positions) == 0:
            return None, None
        return np.min(positions) - self.width / 2, np.max(positions) + self.width / 2

    def _set_view_slice(self) -> None:
        self.events.set_data()

    def _update_thumbnail(self) -> None:
        thumbnail = np.zeros(self._thumbnail_shape)
        thumbnail[..., 3] = self.opacity
        self.thumbnail = thumbnail


def _select_bar(layer: Bar, event) -> None:
    """Select a bar on Shift-click without replacing pan/zoom interaction."""
    if event.type != "mouse_press" or "Shift" not in event.modifiers:
        return
    index = layer.get_value(event.position, world=True)
    if index is None:
        layer.selected_data = set()
    elif index in layer.selected_data:
        layer.selected_data = layer.selected_data - {index}
    else:
        layer.selected_data = layer.selected_data | {index}


__all__ = ["Bar", "BarOrientation"]
