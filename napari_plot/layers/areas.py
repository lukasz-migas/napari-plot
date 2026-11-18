"""Many filled regions between two curves, drawn in one layer."""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import Any

import numpy as np
from napari.layers.base import ActionType
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import Event
from numpy.typing import ArrayLike

from napari_plot.layers.band import band_triangles
from napari_plot.layers.base import BaseLayer


class AreasOrientation(StrEnum):
    """Which axis the shared ``t`` coordinate of every area runs along."""

    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"


def _area_data(data: Any) -> list[np.ndarray]:
    """Validate a sequence of (t, lo, hi) arrays."""
    if data is None:
        return []
    if isinstance(data, np.ndarray) and data.ndim == 2:
        data = [data]
    areas = []
    for area in data:
        values = np.asarray(area, dtype=float)
        if values.ndim != 2 or values.shape[1] != 3 or len(values) < 2:
            raise ValueError("Each area must be an (N >= 2, 3) array of (t, lo, hi) rows.")
        if not np.isfinite(values).all():
            raise ValueError("Area coordinates must be finite.")
        areas.append(values)
    return areas


def _coerce_colors(value: Any, count: int, name: str) -> np.ndarray:
    """Normalize one or many colors to one RGBA row per area."""
    if count == 0:
        return np.empty((0, 4), dtype=float)
    colors = transform_color(value)
    if len(colors) == 1:
        return np.broadcast_to(colors, (count, 4)).copy()
    if len(colors) != count:
        raise ValueError(f"{name} must contain one color or one color per area.")
    return np.asarray(colors, dtype=float)


class Areas(BaseLayer):
    """Fill many regions, each between a lower and an upper curve.

    Parameters
    ----------
    data : sequence of array-like
        One ``(N, 3)`` array of ``(t, lo, hi)`` rows per area. With ``vertical`` orientation ``t`` is
        the x coordinate and ``lo``/``hi`` are y values (like ``Band``); with ``horizontal``
        orientation ``t`` is y and ``lo``/``hi`` are x values (e.g. violins of a vertical violinplot).
    orientation : str or AreasOrientation
        Axis along which ``t`` runs.
    fill_color : color or sequence of colors
        Fill color shared by all areas or supplied per area.
    border_color : color or sequence of colors
        Outline color shared by all areas or supplied per area.
    border_width : float
        Outline width in screen pixels. Zero hides outlines.
    """

    def __init__(
        self,
        data: Sequence[ArrayLike] | None = None,
        *,
        orientation: str | AreasOrientation = AreasOrientation.VERTICAL,
        fill_color: Any = "white",
        border_color: Any = "dimgray",
        border_width: float = 1.0,
        axis_labels: Sequence[str] | None = None,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
        scale: Sequence[float] | None = None,
        translate: Sequence[float] | None = None,
        rotate: Any = None,
        shear: Any = None,
        affine: Any = None,
        opacity: float = 1.0,
        blending: str = "translucent",
        experimental_clipping_planes: Any = None,
        projection_mode: str = "none",
        units: Any = None,
        visible: bool = True,
    ) -> None:
        areas = _area_data(data)
        super().__init__(
            areas,
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
        self.events.add(orientation=Event, fill_color=Event, border_color=Event, border_width=Event)
        self._data = areas
        self._orientation = AreasOrientation(orientation)
        self.fill_color = fill_color
        self.border_color = border_color
        self.border_width = border_width

    @property
    def data(self) -> list[np.ndarray]:
        """Areas as a list of (t, lo, hi) arrays."""
        return self._data

    @data.setter
    def data(self, value: Sequence[ArrayLike] | None) -> None:
        areas = _area_data(value)
        old_count = len(self._data)
        self._data = areas
        if len(areas) != old_count:
            fill = self._fill_color[0] if old_count else "white"
            border = self._border_color[0] if old_count else "dimgray"
            self._fill_color = _coerce_colors(fill, len(areas), "fill_color")
            self._border_color = _coerce_colors(border, len(areas), "border_color")
        self._emit_new_data(ActionType.CHANGED)

    @property
    def orientation(self) -> AreasOrientation:
        """Axis along which the shared ``t`` coordinate runs."""
        return self._orientation

    @orientation.setter
    def orientation(self, value: str | AreasOrientation) -> None:
        self._orientation = AreasOrientation(value)
        self.events.orientation()
        self._emit_new_data(ActionType.CHANGED)

    @property
    def fill_color(self) -> np.ndarray:
        """One RGBA fill color per area."""
        return self._fill_color

    @fill_color.setter
    def fill_color(self, value: Any) -> None:
        self._fill_color = _coerce_colors(value, len(self._data), "fill_color")
        self.events.fill_color()

    @property
    def color(self) -> np.ndarray:
        """Compatibility alias for the fill colors."""
        return self.fill_color

    @color.setter
    def color(self, value: Any) -> None:
        self.fill_color = value

    @property
    def border_color(self) -> np.ndarray:
        """One RGBA outline color per area."""
        return self._border_color

    @border_color.setter
    def border_color(self, value: Any) -> None:
        self._border_color = _coerce_colors(value, len(self._data), "border_color")
        self.events.border_color()

    @property
    def border_width(self) -> float:
        """Outline width in screen pixels."""
        return self._border_width

    @border_width.setter
    def border_width(self, value: float) -> None:
        if not np.isfinite(value) or value < 0:
            raise ValueError("Areas border width must be finite and nonnegative.")
        self._border_width = float(value)
        self.events.border_width()

    def _get_state(self) -> dict[str, Any]:
        return dict(
            self._get_base_state(),
            data=[area.copy() for area in self.data],
            orientation=str(self.orientation),
            fill_color=self.fill_color,
            border_color=self.border_color,
            border_width=self.border_width,
        )

    def _to_xy(self, points: np.ndarray) -> np.ndarray:
        """Map (t, value) pairs to (x, y) according to the orientation."""
        return points if self.orientation is AreasOrientation.VERTICAL else points[..., ::-1]

    def _mesh_data(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return flattened (x, y) vertices, triangle faces, and per-face colors."""
        triangles, colors = [], []
        for area, color in zip(self.data, self.fill_color, strict=True):
            area_triangles = band_triangles(area[:-1], area[1:])
            triangles.append(area_triangles)
            colors.append(np.broadcast_to(color, (len(area_triangles), 4)))
        if not triangles:
            return np.empty((0, 2)), np.empty((0, 3), dtype=np.uint32), np.empty((0, 4))
        vertices = self._to_xy(np.concatenate(triangles).reshape(-1, 2))
        faces = np.arange(len(vertices), dtype=np.uint32).reshape(-1, 3)
        return vertices, faces, np.concatenate(colors)

    def _border_data(self) -> tuple[np.ndarray, np.ndarray]:
        """Return closed-outline line-segment vertices and matching colors."""
        segments, colors = [], []
        for area, color in zip(self.data, self.border_color, strict=True):
            outline = np.concatenate((area[:, [0, 1]], area[::-1, [0, 2]], area[:1, [0, 1]]))
            pairs = np.stack((outline[:-1], outline[1:]), axis=1).reshape(-1, 2)
            segments.append(pairs)
            colors.append(np.broadcast_to(color, (len(pairs), 4)))
        if not segments:
            return np.empty((0, 2)), np.empty((0, 4))
        return self._to_xy(np.concatenate(segments)), np.concatenate(colors)

    def _bounds(self) -> tuple[np.ndarray, np.ndarray]:
        """Return per-area (t_min, t_max) and (value_min, value_max)."""
        t = np.array([(area[:, 0].min(), area[:, 0].max()) for area in self.data])
        v = np.array([(area[:, 1:].min(), area[:, 1:].max()) for area in self.data])
        return t, v

    @property
    def _extent_data(self) -> np.ndarray:
        if not self.data:
            return np.full((2, 2), np.nan)
        t, v = self._bounds()
        t_range = (t[:, 0].min(), t[:, 1].max())
        v_range = (v[:, 0].min(), v[:, 1].max())
        x_range, y_range = (t_range, v_range) if self.orientation is AreasOrientation.VERTICAL else (v_range, t_range)
        return np.array([[y_range[0], x_range[0]], [y_range[1], x_range[1]]])

    def _get_x_region_extent(self, x_min: float, x_max: float) -> tuple[float | None, float | None]:
        """Return the y extent of areas intersecting an x-axis interval."""
        if not self.data:
            return None, None
        t, v = self._bounds()
        x_bounds, y_bounds = (t, v) if self.orientation is AreasOrientation.VERTICAL else (v, t)
        mask = (x_bounds[:, 1] >= x_min) & (x_bounds[:, 0] <= x_max)
        if not mask.any():
            return None, None
        return float(y_bounds[mask, 0].min()), float(y_bounds[mask, 1].max())

    def _set_view_slice(self) -> None:
        self.events.set_data()

    def _update_thumbnail(self) -> None:
        if hasattr(self, "_fill_color") and len(self._fill_color):
            thumbnail = np.broadcast_to(self._fill_color[0], self._thumbnail_shape).copy()
            thumbnail[..., 3] *= self.opacity
            self.thumbnail = thumbnail

    def _get_value(self, position: Sequence[float]) -> int | None:
        """Return the topmost area containing a data-space ``(y, x)`` position."""
        if not self.data:
            return None
        y, x = float(position[-2]), float(position[-1])
        t, value = (x, y) if self.orientation is AreasOrientation.VERTICAL else (y, x)
        for index in range(len(self.data) - 1, -1, -1):
            area = self.data[index]
            order = np.argsort(area[:, 0], kind="stable")
            support = area[order, 0]
            if not support[0] <= t <= support[-1]:
                continue
            lo, hi = np.interp(t, support, area[order, 1]), np.interp(t, support, area[order, 2])
            if min(lo, hi) <= value <= max(lo, hi):
                return index
        return None


__all__ = ["Areas", "AreasOrientation"]
