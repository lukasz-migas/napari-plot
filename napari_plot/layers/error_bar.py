"""Horizontal and vertical error intervals."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
from napari.layers.base import ActionType
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import Event
from numpy.typing import ArrayLike

from napari_plot.layers.base import BaseLayer


def _error_bar_data(data: ArrayLike | None) -> np.ndarray:
    """Validate centers and paired error offsets."""
    values = np.asarray(data, dtype=float) if data is not None else np.empty((0, 6))
    if values.shape == (0,):
        values = values.reshape(0, 6)
    if values.ndim != 2 or values.shape[1] != 6:
        raise ValueError("ErrorBar data must contain (x, y, x_minus, x_plus, y_minus, y_plus) rows.")
    offsets = values[:, 2:]
    missing = np.isnan(offsets)
    if not np.isfinite(values[:, :2]).all():
        raise ValueError("ErrorBar centers must be finite.")
    if np.any(offsets < 0) or np.isinf(offsets).any() or np.any(missing[:, ::2] != missing[:, 1::2]):
        raise ValueError("ErrorBar offsets must be finite and nonnegative, or both NaN for an omitted interval.")
    return values


class ErrorBar(BaseLayer):
    """Draw error intervals around a set of points.

    Data contains (x, y, x_minus, x_plus, y_minus, y_plus) rows. Offsets
    are nonnegative and measured in axis units. A pair of NaNs omits that axis.
    Width and cap size are in screen pixels.
    """

    def __init__(
        self,
        data: ArrayLike | None = None,
        *,
        color: Any = "white",
        width: float = 1.0,
        cap_size: float = 6.0,
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
        values = _error_bar_data(data)
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
        self.events.add(color=Event, width=Event, cap_size=Event)
        self._data = values
        self.color = color
        self.width = width
        self.cap_size = cap_size

    @property
    def data(self) -> np.ndarray:
        """Point centers followed by the lower and upper offsets for x and y."""
        return self._data

    @data.setter
    def data(self, value: ArrayLike | None) -> None:
        self._data = _error_bar_data(value)
        self._emit_new_data(ActionType.CHANGED)

    @property
    def color(self) -> np.ndarray:
        """Color of stems and caps as one RGBA value."""
        return self._color

    @color.setter
    def color(self, value: Any) -> None:
        colors = transform_color(value)
        if len(colors) != 1:
            raise ValueError("ErrorBar color must be a single color.")
        self._color = colors[0]
        self.events.color()

    @property
    def width(self) -> float:
        """Thickness of stems and caps in screen pixels."""
        return self._width

    @width.setter
    def width(self, value: float) -> None:
        if not np.isfinite(value) or value <= 0:
            raise ValueError("ErrorBar width must be finite and positive.")
        self._width = float(value)
        self.events.width()

    @property
    def cap_size(self) -> float:
        """Full length of the caps in screen pixels. Zero hides caps."""
        return self._cap_size

    @cap_size.setter
    def cap_size(self, value: float) -> None:
        if not np.isfinite(value) or value < 0:
            raise ValueError("ErrorBar cap size must be finite and nonnegative.")
        self._cap_size = float(value)
        self.events.cap_size()

    def _get_state(self) -> dict[str, Any]:
        return dict(self._get_base_state(), data=self.data, color=self.color, width=self.width, cap_size=self.cap_size)

    def _segments(self) -> np.ndarray:
        """Return the (x, y) endpoints of each supplied interval."""
        data = self.data
        segments = np.broadcast_to(data[:, None, None, :2], (len(data), 2, 2, 2)).copy()
        segments[:, 0, 0, 0] -= data[:, 2]
        segments[:, 0, 1, 0] += data[:, 3]
        segments[:, 1, 0, 1] -= data[:, 4]
        segments[:, 1, 1, 1] += data[:, 5]
        return segments[~np.isnan(data[:, 2::2])]

    @property
    def _extent_data(self) -> np.ndarray:
        endpoints = self._segments().reshape(-1, 2)
        if not len(endpoints):
            return np.full((2, 2), np.nan)
        return np.vstack((endpoints.min(axis=0)[::-1], endpoints.max(axis=0)[::-1]))

    def _get_x_region_extent(self, x_min: float, x_max: float) -> tuple[float | None, float | None]:
        segments = self._segments()
        intersects = (segments[:, 0, 0] <= x_max) & (segments[:, 1, 0] >= x_min)
        if not intersects.any():
            return None, None
        y = segments[intersects, :, 1]
        return float(y.min()), float(y.max())

    def _set_view_slice(self) -> None:
        self.events.set_data()

    def _update_thumbnail(self) -> None:
        if hasattr(self, "_color"):
            thumbnail = np.broadcast_to(self.color, self._thumbnail_shape).copy()
            thumbnail[..., 3] *= self.opacity
            self.thumbnail = thumbnail

    def _get_value(self, position: Sequence[float]) -> None:
        return None
