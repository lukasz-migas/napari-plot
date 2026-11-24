"""Helpers for finding the data point under the cursor and describing it.

Adapted from ionglow's line hover readout. Layers implement ``_get_hover_point`` with these helpers, and the viewer
combines their answers into a :class:`HoverInfo` shown by the hover overlay.
"""

from __future__ import annotations

import typing as ty
from dataclasses import dataclass

import numpy as np

if ty.TYPE_CHECKING:
    from napari_plot.components.axis import AxisScale

# half-width, in screen pixels, of the window searched for the highest point of a curve around the cursor
SNAP_PIXELS = 2.0
# largest distance, in screen pixels, at which a scatter point is picked
POINT_PIXELS = 8.0
# longest curve label shown in a multi-curve readout; longer labels are elided in the middle
MAX_LABEL_LENGTH = 40


def _to_axis(values: ty.Any, scale: AxisScale | str, power: float) -> np.ndarray:
    """Map data values to displayed axis coordinates; non-positive values become NaN on a log axis."""
    # imported here: the components package imports this module
    from napari_plot.components.axis import AxisScale, transform_axis_values

    values = np.asarray(values, dtype=float)
    if AxisScale(scale) is AxisScale.LOG:
        positive = values > 0
        return np.where(positive, np.log10(np.where(positive, values, 1.0)), np.nan)
    return np.asarray(transform_axis_values(values, scale, power=power), dtype=float)


@dataclass(frozen=True)
class PixelMapper:
    """Map data coordinates to screen pixels of the plot area.

    ``rect`` is the visible ``(xmin, xmax, ymin, ymax)`` range in data units and ``size`` the ``(width, height)`` of
    the plot area in pixels. Log and power axes are taken into account.
    """

    rect: tuple[float, float, float, float]
    size: tuple[float, float]
    x_scale: AxisScale | str = "linear"
    y_scale: AxisScale | str = "linear"
    x_power: float = 2.0
    y_power: float = 2.0

    def _pixels_per_unit(self) -> tuple[float, float]:
        """Pixels per displayed axis unit along x and y."""
        xmin, xmax, ymin, ymax = self.rect
        x_low, x_high = _to_axis([xmin, xmax], self.x_scale, self.x_power)
        y_low, y_high = _to_axis([ymin, ymax], self.y_scale, self.y_power)
        tiny = np.finfo(float).tiny
        width, height = self.size
        return width / max(abs(float(x_high - x_low)), tiny), height / max(abs(float(y_high - y_low)), tiny)

    def to_pixels(self, x: ty.Any, y: ty.Any) -> tuple[np.ndarray, np.ndarray]:
        """Convert data coordinates to pixels; only differences between results are meaningful."""
        x_ppu, y_ppu = self._pixels_per_unit()
        return _to_axis(x, self.x_scale, self.x_power) * x_ppu, _to_axis(y, self.y_scale, self.y_power) * y_ppu

    def _window(
        self, value: float, pixels: float, scale: AxisScale | str, power: float, ppu: float
    ) -> tuple[float, float]:
        from napari_plot.components.axis import transform_axis_values

        center = float(_to_axis(value, scale, power))
        if not np.isfinite(center) or ppu <= 0:
            return value, value
        half = pixels / ppu
        low, high = transform_axis_values(np.array([center - half, center + half]), scale, inverse=True, power=power)
        return float(low), float(high)

    def x_window(self, x: float, pixels: float) -> tuple[float, float]:
        """Data range along x covered by ``pixels`` screen pixels on each side of ``x``."""
        return self._window(x, pixels, self.x_scale, self.x_power, self._pixels_per_unit()[0])

    def y_window(self, y: float, pixels: float) -> tuple[float, float]:
        """Data range along y covered by ``pixels`` screen pixels on each side of ``y``."""
        return self._window(y, pixels, self.y_scale, self.y_power, self._pixels_per_unit()[1])


def nearest_index(x: np.ndarray, value: float) -> int | None:
    """Index of the point of a monotonic ``x`` nearest to ``value``, or None more than half a step outside ``x``."""
    x = np.asarray(x)
    n = x.size
    if n == 0:
        return None
    if n == 1:
        return 0
    descending = x[0] > x[-1]
    ordered = x[::-1] if descending else x
    position = int(np.searchsorted(ordered, value))
    if position == 0:
        index = 0
        outside = ordered[0] - value > (ordered[1] - ordered[0]) / 2
    elif position == n:
        index = n - 1
        outside = value - ordered[-1] > (ordered[-1] - ordered[-2]) / 2
    else:
        index = position if ordered[position] - value < value - ordered[position - 1] else position - 1
        outside = False
    if outside:
        return None
    return n - 1 - index if descending else index


def snap_index(x: np.ndarray, y: np.ndarray, value: float, low: float, high: float) -> int | None:
    """Index of the highest point with ``low <= x <= high`` in a monotonic ``x``, else of the point nearest ``value``."""
    x, y = np.asarray(x), np.asarray(y)
    if high > low and x.size > 1:
        descending = x[0] > x[-1]
        ordered = x[::-1] if descending else x
        start = int(np.searchsorted(ordered, low, side="left"))
        stop = int(np.searchsorted(ordered, high, side="right"))
        if stop > start:
            if descending:
                start, stop = x.size - stop, x.size - start
            return start + int(np.argmax(y[start:stop]))
    return nearest_index(x, value)


def elide_middle(text: str, max_length: int = MAX_LABEL_LENGTH) -> str:
    """Shorten ``text`` to ``max_length`` characters by replacing its middle with '...'."""
    if len(text) <= max_length:
        return text
    keep = max_length - 3
    head = (keep + 1) // 2
    return f"{text[:head]}...{text[len(text) - (keep - head) :]}"


def format_value(value: float) -> str:
    """Format a coordinate or data value compactly."""
    return f"{value:,.6g}"


def format_coordinates(x: float, y: float) -> str:
    """Format a cursor position for the status bar and the crosshair label."""
    return f"x={format_value(x)}, y={format_value(y)}"


@dataclass(frozen=True)
class HoverPoint:
    """Data point a layer reports under the cursor: its coordinates, index in the layer and label."""

    x: float
    y: float
    index: int
    label: str = ""


@dataclass(frozen=True)
class HoverInfo:
    """Data point under the cursor, with the values of the other layers hit at the same position.

    ``x`` and ``y`` are the snapped point (``index``) of the layer ``label``; ``rows`` hold (label, y) for every other
    layer with a point under the cursor.
    """

    x: float
    y: float
    index: int
    label: str
    x_label: str = ""
    y_label: str = ""
    rows: tuple[tuple[str, float], ...] = ()

    def format(self) -> str:
        """Text shown in the hover overlay."""
        lines = [f"{self.x_label or 'x'}: {format_value(self.x)}"]
        if self.rows:
            rows = ((self.label, self.y), *self.rows)
            lines.extend(f"{elide_middle(label)}: {format_value(value)}" for label, value in rows)
        else:
            lines.append(f"{self.y_label or 'y'}: {format_value(self.y)}")
        return "\n".join(lines)
