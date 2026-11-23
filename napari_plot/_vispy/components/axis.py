"""Reimplementation of axis-visual"""

from __future__ import annotations

import inspect
import typing as ty
from datetime import UTC, datetime, timedelta
from functools import partial
from itertools import pairwise

import numpy as np
import vispy.visuals.axis
from qtpy.QtGui import QFont, QFontMetricsF
from vispy.visuals.axis import Ticker as _Ticker, _get_ticks_talbot

from napari_plot.components.axis import UNIX_EPOCH, AxisScale, TickNotation, transform_axis_values


def default_tick_formatter(value: float) -> str:
    """Format a number as a compact tick label."""
    return f"{value:g}"


_INITIAL_TICK_DENSITY = 2.0
_DENSITY_REDUCTION = 0.75
_MAX_DENSITY_PASSES = 8
_MIN_LABEL_GAP = 4.0


def _accepts_tick_spacing(formatter: ty.Callable[..., str]) -> bool:
    """Return whether a formatter opts into tick-spacing context."""
    try:
        parameters = inspect.signature(formatter).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        or (parameter.name == "tick_spacing" and parameter.kind is not inspect.Parameter.POSITIONAL_ONLY)
        for parameter in parameters
    )


def _format_ticks(
    formatter: ty.Callable[..., str],
    values: np.ndarray,
    tick_spacing: float | None,
) -> list[str]:
    """Format tick values, providing spacing to formatters that request it."""
    if _accepts_tick_spacing(formatter):
        return [formatter(float(value), tick_spacing=tick_spacing) for value in values]
    return [formatter(float(value)) for value in values]


def _thin_label_sequence(
    axis: ty.Any,
    positions: np.ndarray,
    labels: list[str],
    domain: np.ndarray,
) -> list[str]:
    """Hide labels at a stable stride until the remaining labels fit."""
    visible_indices = np.flatnonzero(_visible_tick_mask(positions, domain))
    if len(visible_indices) == 0:
        return [""] * len(labels)

    for stride in range(2, len(labels) + 1):
        phase = int(visible_indices[0] % stride)
        thinned = [label if index % stride == phase else "" for index, label in enumerate(labels)]
        if not _tick_labels_overlap(axis, positions, thinned, domain):
            return thinned
    return [""] * len(labels)


def _visible_tick_mask(values: np.ndarray, domain: np.ndarray) -> np.ndarray:
    """Return ticks that fall within the visible domain."""
    scale = float(domain[1] - domain[0])
    if scale == 0:
        return np.ones(len(values), dtype=bool)
    fractions = (values - domain[0]) / scale
    return (fractions > -0.0001) & (fractions < 1.0001)


def _tick_label_sizes(axis: ty.Any, labels: ty.Sequence[str]) -> tuple[np.ndarray, np.ndarray]:
    """Measure the unrotated width and height of each label in logical pixels."""
    text = axis._text
    font = QFont(text.face)
    font.setPointSizeF(float(axis.tick_font_size))
    font.setBold(bool(text.bold))
    font.setItalic(bool(text.italic))
    metrics = QFontMetricsF(font)

    font_dpi = float(metrics.fontDpi())
    dpi_scale = float(axis.transforms.dpi) / font_dpi if font_dpi > 0 else 1.0
    # labels may span several lines (e.g. wrapped categories): use the widest line and the stacked height
    widths = np.asarray(
        [max(metrics.horizontalAdvance(line) for line in label.split("\n")) for label in labels], dtype=float
    )
    heights = np.asarray([metrics.height() * (label.count("\n") + 1) for label in labels], dtype=float)
    return widths * dpi_scale, heights * dpi_scale


def _label_rotation(axis: ty.Any) -> float:
    """Return the counter-clockwise tick label rotation of `axis` in degrees."""
    return float(getattr(getattr(axis, "ticker", None), "label_rotation", 0.0))


def _tick_label_extents(axis: ty.Any, labels: list[str]) -> np.ndarray:
    """Measure the space each label needs along the axis in logical pixels.

    Rotated labels are parallel boxes, so neighbours are clear once they are separated either along the text direction
    (by the label width) or across it (by the label height), whichever needs the shorter distance along the axis.
    """
    widths, heights = _tick_label_sizes(axis, labels)
    axis_vector = np.asarray(axis.pos[1] - axis.pos[0], dtype=float)
    axis_length = float(np.linalg.norm(axis_vector))
    if axis_length == 0:
        return np.zeros(len(labels), dtype=float)
    direction = np.abs(axis_vector[:2]) / axis_length
    rotation = np.radians(_label_rotation(axis))
    if rotation == 0:
        return direction[0] * widths + direction[1] * heights
    cos, sin = abs(np.cos(rotation)), abs(np.sin(rotation))
    with np.errstate(divide="ignore"):
        along_horizontal = np.minimum(widths / cos, heights / sin)
        along_vertical = np.minimum(heights / cos, widths / sin)
    return direction[0] * along_horizontal + direction[1] * along_vertical


def rotated_label_growth(axis: ty.Any, labels: ty.Sequence[str], rotation: float) -> float:
    """Return how much taller (in logical pixels) the tallest label of a horizontal axis gets when rotated."""
    if not labels or rotation == 0:
        return 0.0
    widths, heights = _tick_label_sizes(axis, labels)
    angle = np.radians(rotation)
    rotated = widths * abs(np.sin(angle)) + heights * abs(np.cos(angle))
    return max(0.0, float(np.max(rotated) - np.max(heights)))


def _tick_labels_overlap(
    axis: ty.Any,
    values: np.ndarray,
    labels: list[str],
    domain: np.ndarray,
) -> bool:
    """Return whether adjacent visible tick labels overlap."""
    visible = _visible_tick_mask(values, domain)
    visible &= np.asarray([bool(label) for label in labels], dtype=bool)
    if np.count_nonzero(visible) < 2:
        return False

    visible_values = values[visible]
    visible_labels = [label for label, is_visible in zip(labels, visible, strict=True) if is_visible]
    extents = _tick_label_extents(axis, visible_labels)
    axis_length = float(np.linalg.norm(axis.pos[1] - axis.pos[0]))
    scale = float(domain[1] - domain[0])
    if scale == 0:
        return False
    positions = (visible_values - domain[0]) / scale * axis_length
    gaps = np.abs(np.diff(positions))
    required_gaps = (extents[:-1] + extents[1:]) / 2 + _MIN_LABEL_GAP
    return bool(np.any(gaps < required_gaps))


def _thin_overlapping_labels(
    axis: ty.Any,
    major: np.ndarray,
    formatter: ty.Callable[..., str],
    domain: np.ndarray,
) -> list[str]:
    """Deterministically hide labels until the remaining labels fit."""
    base_step = float(abs(major[1] - major[0]))
    visible_indices = np.flatnonzero(_visible_tick_mask(major, domain))
    if len(visible_indices) == 0:
        return [""] * len(major)

    for stride in range(2, len(major) + 1):
        labels = _format_ticks(formatter, major, base_step * stride)
        phase = int(visible_indices[0] % stride)
        labels = [label if index % stride == phase else "" for index, label in enumerate(labels)]
        if not _tick_labels_overlap(axis, major, labels, domain):
            return labels
    return [""] * len(major)


def _get_major_ticks(
    axis: ty.Any,
    formatter: ty.Callable[..., str],
    domain: np.ndarray,
    n_inches: float,
) -> tuple[np.ndarray, list[str]]:
    """Return nice major ticks with labels adapted to the available space."""
    density = _INITIAL_TICK_DENSITY
    for _ in range(_MAX_DENSITY_PASSES):
        major = _get_ticks_talbot(domain[0], domain[1], n_inches, density)
        spacing = float(abs(major[1] - major[0]))
        labels = _format_ticks(formatter, major, spacing)
        if not _tick_labels_overlap(axis, major, labels, domain):
            return major, labels
        density *= _DENSITY_REDUCTION
    return major, _thin_overlapping_labels(axis, major, formatter, domain)


def _get_log_ticks(
    axis: ty.Any,
    formatter: ty.Callable[..., str],
    domain: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Return base-10 logarithmic major ticks, minor ticks, and labels."""
    start, stop = float(domain[0]), float(domain[1])
    major = np.arange(np.ceil(start), np.floor(stop) + 1.0)
    if np.count_nonzero(_visible_tick_mask(major, domain)) < 2:
        decades = np.arange(np.floor(start) - 1.0, np.ceil(stop) + 1.0)
        subdivisions = np.log10(np.asarray([1.0, 2.0, 5.0]))
        major = np.sort((decades[:, None] + subdivisions).ravel())

    if np.count_nonzero(_visible_tick_mask(major, domain)) < 2:
        raw_domain = np.power(10.0, domain)
        length = np.linalg.norm(axis.pos[1] - axis.pos[0])
        n_inches = float(length / axis.transforms.dpi)
        density = _INITIAL_TICK_DENSITY
        for _ in range(_MAX_DENSITY_PASSES):
            raw_major = _get_ticks_talbot(*raw_domain, n_inches, density)
            raw_major = raw_major[raw_major > 0]
            major = np.log10(raw_major)
            spacing = float(abs(raw_major[1] - raw_major[0]))
            labels = _format_ticks(formatter, raw_major, spacing)
            if not _tick_labels_overlap(axis, major, labels, domain):
                break
            density *= _DENSITY_REDUCTION
        else:
            labels = _thin_label_sequence(axis, major, labels, domain)

        minor_values = np.concatenate([np.linspace(left, right, 6)[1:-1] for left, right in pairwise(raw_major)])
        return major, np.log10(minor_values), labels

    values = np.power(10.0, major)
    labels = _format_ticks(formatter, values, None)
    if _tick_labels_overlap(axis, major, labels, domain):
        labels = _thin_label_sequence(axis, major, labels, domain)

    decades = np.arange(np.floor(start) - 1.0, np.ceil(stop) + 1.0)
    subdivisions = np.log10(np.arange(2.0, 10.0))
    minor = np.sort((decades[:, None] + subdivisions).ravel())
    for position in major:
        minor = minor[~np.isclose(minor, position)]
    return major, minor, labels


def _get_categorical_ticks(
    axis: ty.Any,
    category_labels: tuple[str, ...],
    domain: np.ndarray,
    thin: bool = True,
) -> tuple[np.ndarray, list[str]]:
    """Return integer tick positions and ordered categorical labels, hiding overlapping labels when `thin`."""
    major = np.arange(len(category_labels), dtype=float)
    labels = list(category_labels)
    if thin and _tick_labels_overlap(axis, major, labels, domain):
        labels = _thin_label_sequence(axis, major, labels, domain)
    return major, labels


def _datetime_tick_formatter(origin: datetime, value: float, *, tick_spacing: float | None = None) -> str:
    """Choose date and time precision using the distance between labels."""
    tick_spacing = tick_spacing or 0.0
    if tick_spacing >= 86_400:
        format_string = "%Y-%m-%d"
    elif tick_spacing >= 60:
        format_string = "%m-%d %H:%M"
    else:
        format_string = "%H:%M:%S"
    try:
        if origin.tzinfo is None:
            origin = origin.replace(tzinfo=UTC)
        timestamp = (origin.astimezone(UTC) + timedelta(seconds=value)).astimezone(origin.tzinfo)
    except OverflowError:
        return default_tick_formatter(value)
    result = timestamp.strftime(format_string)
    if tick_spacing < 1 and timestamp.microsecond:
        result += f".{timestamp.microsecond:06d}".rstrip("0")
    return result


class Ticker(_Ticker):
    """Monkey-patched Ticker class"""

    def __init__(self, axis, anchors=None, tick_format_func=default_tick_formatter):
        super().__init__(axis, anchors)
        self.tick_format_func = tick_format_func
        self.category_labels: tuple[str, ...] = ()
        self.thin_categories = True
        self.label_rotation = 0.0  # degrees, counter-clockwise
        self.major_tick_origins = np.empty((0, 2))
        self.minor_tick_origins = np.empty((0, 2))
        self.minor_ticks = True
        self.notation = TickNotation.DEFAULT
        self.power = 2.0
        self.datetime_origin = UNIX_EPOCH
        self.axis_label: str | None = None
        self._number_offset = 0.0

    def _get_tick_positions(
        self, major_tick_fractions: np.ndarray, minor_tick_fractions: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, ty.Sequence[str]]:
        """Save the major tick origins from the layout used to draw the marks."""
        # Keep minor coordinates for the grid independently of the minor tick marks.
        tick_fractions = minor_tick_fractions if self.minor_ticks else np.empty(0)
        positions, label_pos, axis_label_pos, anchors = super()._get_tick_positions(
            major_tick_fractions, tick_fractions
        )
        end = 2 * len(major_tick_fractions)
        self.major_tick_origins = positions[:end:2]
        self.minor_tick_origins = self.axis.pos[0] + minor_tick_fractions[:, None] * self.axis._vec
        return positions, label_pos, axis_label_pos, anchors

    def _formatter(self, domain: np.ndarray) -> ty.Callable[..., str]:
        """Choose a formatter for the current axis and compute its shared offset."""
        self._number_offset = 0.0
        if self.tick_format_func not in (None, default_tick_formatter):
            return self.tick_format_func
        if self.axis.scale_type == "datetime":
            return partial(_datetime_tick_formatter, self.datetime_origin)
        if self.notation is TickNotation.SCIENTIFIC:
            return lambda value: f"{value:.3e}"
        if self.notation is TickNotation.OFFSET and self.axis.scale_type == "linear":
            span = float(domain[1] - domain[0])
            if span > 0 and abs(domain[0]) >= 100 * span:
                unit = 10.0 ** np.ceil(np.log10(span))
                self._number_offset = float(np.floor(domain[0] / unit) * unit)
            return lambda value: default_tick_formatter(value - self._number_offset)
        return default_tick_formatter

    def _get_tick_frac_labels(self) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """Return visible major and minor tick positions and the major labels."""
        displayed_domain = np.asarray(self.axis.domain, dtype=float)
        flip = displayed_domain[1] < displayed_domain[0]
        domain = displayed_domain[::-1] if flip else displayed_domain
        scale_type = self.axis.scale_type
        formatter = self._formatter(domain)
        if scale_type == "categorical":
            major, labels = _get_categorical_ticks(
                self.axis,
                self.category_labels,
                domain,
                thin=self.thin_categories,
            )
            minor = np.empty(0)
        elif scale_type == "logarithmic" and domain[0] != domain[1]:
            major, minor, labels = _get_log_ticks(self.axis, formatter, domain)
        elif scale_type == "power" and domain[0] != domain[1]:
            # Tick spacing is uniform in the transformed coordinates. Labels show the original values.
            major, minor, labels = self._get_linear_ticks(
                domain,
                lambda value: formatter(transform_axis_values(value, AxisScale.POWER, inverse=True, power=self.power)),
            )
        elif domain[0] == domain[1]:
            value = float(domain[0])
            if scale_type in ("logarithmic", "power"):
                scale = AxisScale.LOG if scale_type == "logarithmic" else AxisScale.POWER
                value = transform_axis_values(value, scale, inverse=True, power=self.power)
            major, minor, labels = domain[:1], np.empty(0), _format_ticks(formatter, np.array([value]), None)
        else:
            major, minor, labels = self._get_linear_ticks(domain, formatter)

        if self.axis_label is not None:
            suffix = f" ({self._number_offset:+g})" if self._number_offset else ""
            self.axis._axis_label = self.axis_label + suffix
        span = float(domain[1] - domain[0])
        if span == 0:
            use_mask = np.isclose(major, domain[0], rtol=0)
            visible_labels = [label for label, keep in zip(labels, use_mask, strict=True) if keep]
            return np.full(int(use_mask.sum()), 0.5), np.empty(0), visible_labels
        major_frac = (major - domain[0]) / span
        minor_frac = (minor - domain[0]) / span
        if flip:
            major_frac = 1 - major_frac
            minor_frac = 1 - minor_frac
        use_mask = _visible_tick_mask(major, domain)
        return (
            major_frac[use_mask],
            minor_frac[_visible_tick_mask(minor, domain)],
            [label for label, keep in zip(labels, use_mask, strict=True) if keep],
        )

    def _get_linear_ticks(
        self, domain: np.ndarray, formatter: ty.Callable[..., str]
    ) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """Find major labels and four minor ticks between each major pair."""
        length = np.linalg.norm(self.axis.pos[1] - self.axis.pos[0])
        major, labels = _get_major_ticks(self.axis, formatter, domain, length / self.axis.transforms.dpi)
        step = major[1] - major[0]
        start = 0 if self.axis._stop_at_major[0] else -1
        stop = len(major) - int(self.axis._stop_at_major[1])
        intervals = np.arange(start, stop)[:, None] + np.arange(1, 5) / 5
        return major, (major[0] + step * intervals).ravel(), labels


vispy.visuals.axis.Ticker = Ticker
