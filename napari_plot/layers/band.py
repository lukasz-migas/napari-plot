"""Filled region between two curves on a shared x grid."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
from napari.layers.base import ActionType
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import Event
from numpy.typing import ArrayLike

from napari_plot.layers.base import BaseLayer


def _band_data(data: ArrayLike | None) -> np.ndarray:
    """Validate rows while retaining NaN bounds as gaps."""
    values = np.asarray(data, dtype=float) if data is not None else np.empty((0, 3))
    if values.shape == (0,):
        values = values.reshape(0, 3)
    if values.ndim != 2 or values.shape[1] != 3:
        raise ValueError("Band data must contain (x, y1, y2) rows.")
    x = values[:, 0]
    if not np.isfinite(x).all() or np.isinf(values[:, 1:]).any():
        raise ValueError("Band x coordinates must be finite and bounds must be finite or NaN.")
    if not (np.all(x[1:] > x[:-1]) or np.all(x[1:] < x[:-1])):
        raise ValueError("Band x coordinates must be strictly increasing or decreasing.")
    return values


def band_triangles(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """Return (M, 3, 2) fill triangles between paired (t, lo, hi) interval endpoints.

    Each ``left[i]``/``right[i]`` pair describes one connected interval. Intervals in which
    the two bounds cross are split at the intersection so the fill never folds over itself.
    """
    left1, left2 = left[:, [0, 1]], left[:, [0, 2]]
    right1, right2 = right[:, [0, 1]], right[:, [0, 2]]
    triangles = np.stack((left1, left2, right1, left2, right2, right1), axis=1)
    left_delta = left[:, 1] - left[:, 2]
    right_delta = right[:, 1] - right[:, 2]
    crossing = ((left_delta < 0) & (right_delta > 0)) | ((left_delta > 0) & (right_delta < 0))
    fraction = (left_delta[crossing] / (left_delta[crossing] - right_delta[crossing]))[:, None]
    intersection = left1[crossing] + fraction * (right1[crossing] - left1[crossing])
    triangles[crossing, 2] = intersection
    triangles[crossing, 3] = intersection
    return triangles.reshape(-1, 3, 2)


class Band(BaseLayer):
    """Fill between two curves.

    Data contains (x, y1, y2) rows with strictly monotonic x coordinates.
    NaN in either bound creates a gap. Curves may cross.
    """

    def __init__(
        self,
        data: ArrayLike | None = None,
        *,
        fill_color: Any = "white",
        axis_labels: Sequence[str] | None = None,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
        scale: Sequence[float] | None = None,
        translate: Sequence[float] | None = None,
        rotate: Any = None,
        shear: Any = None,
        affine: Any = None,
        opacity: float = 0.3,
        blending: str = "translucent",
        experimental_clipping_planes: Any = None,
        projection_mode: str = "none",
        units: Any = None,
        visible: bool = True,
    ) -> None:
        values = _band_data(data)
        super().__init__(
            values,
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
        self.events.add(fill_color=Event)
        self._data = values
        self.fill_color = fill_color

    @property
    def data(self) -> np.ndarray:
        """Band coordinates as (x, y1, y2) rows."""
        return self._data

    @data.setter
    def data(self, value: ArrayLike | None) -> None:
        self._data = _band_data(value)
        self._emit_new_data(ActionType.CHANGED)

    @property
    def fill_color(self) -> np.ndarray:
        """Fill color as one RGBA value."""
        return self._fill_color

    @fill_color.setter
    def fill_color(self, value: Any) -> None:
        colors = transform_color(value)
        if len(colors) != 1:
            raise ValueError("Band fill_color must be a single color.")
        self._fill_color = colors[0]
        self.events.fill_color()

    def _get_state(self) -> dict[str, Any]:
        return dict(self._get_base_state(), data=self.data, fill_color=self.fill_color)

    def _segments(self) -> tuple[np.ndarray, np.ndarray]:
        valid = np.isfinite(self.data[:, 1:]).all(axis=1)
        connected = valid[:-1] & valid[1:]
        return self.data[:-1][connected], self.data[1:][connected]

    def _triangles(self) -> np.ndarray:
        """Return the two fill triangles for each connected interval."""
        return band_triangles(*self._segments())

    @property
    def _extent_data(self) -> np.ndarray:
        valid = self.data[np.isfinite(self.data[:, 1:]).all(axis=1)]
        if not len(valid):
            return np.full((2, 2), np.nan)
        return np.array([[valid[:, 1:].min(), valid[:, 0].min()], [valid[:, 1:].max(), valid[:, 0].max()]])

    def _get_x_region_extent(self, x_min: float, x_max: float) -> tuple[float | None, float | None]:
        left, right = self._segments()
        lo = np.maximum(np.minimum(left[:, 0], right[:, 0]), x_min)
        hi = np.minimum(np.maximum(left[:, 0], right[:, 0]), x_max)
        intersects = lo <= hi
        if not intersects.any():
            return None, None
        left, right = left[intersects], right[intersects]
        fractions = (np.column_stack((lo[intersects], hi[intersects])) - left[:, :1]) / (right[:, :1] - left[:, :1])
        bounds = left[:, None, 1:] + fractions[:, :, None] * (right - left)[:, None, 1:]
        return float(bounds.min()), float(bounds.max())

    def _set_view_slice(self) -> None:
        self.events.set_data()

    def _update_thumbnail(self) -> None:
        if hasattr(self, "_fill_color"):
            thumbnail = np.broadcast_to(self.fill_color, self._thumbnail_shape).copy()
            thumbnail[..., 3] *= self.opacity
            self.thumbnail = thumbnail

    def _get_value(self, position: Sequence[float]) -> None:
        return None
