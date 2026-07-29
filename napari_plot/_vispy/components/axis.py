"""Reimplementation of axis-visual"""

from __future__ import annotations

import inspect
import typing as ty

import numpy as np
import vispy.visuals.axis
from qtpy.QtGui import QFont, QFontMetricsF
from vispy.visuals.axis import Ticker as _Ticker, _get_ticks_talbot

default_tick_formatter = lambda x: "%g" % x  # noqa

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


def _tick_label_extents(axis: ty.Any, labels: list[str]) -> np.ndarray:
    """Measure label extents projected along the axis in logical pixels."""
    text = axis._text
    font = QFont(text.face)
    font.setPointSizeF(float(axis.tick_font_size))
    font.setBold(bool(text.bold))
    font.setItalic(bool(text.italic))
    metrics = QFontMetricsF(font)

    font_dpi = float(metrics.fontDpi())
    dpi_scale = float(axis.transforms.dpi) / font_dpi if font_dpi > 0 else 1.0
    widths = np.asarray([metrics.horizontalAdvance(label) for label in labels], dtype=float)
    height = float(metrics.height())

    axis_vector = np.asarray(axis.pos[1] - axis.pos[0], dtype=float)
    axis_length = float(np.linalg.norm(axis_vector))
    if axis_length == 0:
        return np.zeros(len(labels), dtype=float)
    direction = np.abs(axis_vector[:2]) / axis_length
    return (direction[0] * widths + direction[1] * height) * dpi_scale


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

        minor_values = np.concatenate(
            [
                np.linspace(left, right, 6)[1:-1]
                for left, right in zip(raw_major[:-1], raw_major[1:], strict=True)
            ]
        )
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


class Ticker(_Ticker):
    """Monkey-patched Ticker class"""

    def __init__(self, axis, anchors=None, tick_format_func=default_tick_formatter):
        super().__init__(axis, anchors)
        self.tick_format_func = tick_format_func

    def _get_tick_frac_labels(self):
        """Get the major ticks, minor ticks, and major labels"""
        minor_num = 4  # number of minor ticks per major division
        if self.axis.scale_type == "linear":
            domain = self.axis.domain
            if domain[1] < domain[0]:
                flip = True
                domain = domain[::-1]
            else:
                flip = False
            offset = domain[0]
            scale = domain[1] - domain[0]

            transforms = self.axis.transforms
            length = self.axis.pos[1] - self.axis.pos[0]  # in logical coords
            n_inches = np.sqrt(np.sum(length**2)) / transforms.dpi

            major, labels = _get_major_ticks(self.axis, self.tick_format_func, domain, n_inches)
            majstep = major[1] - major[0]
            minor = []
            minstep = majstep / (minor_num + 1)
            minstart = 0 if self.axis._stop_at_major[0] else -1
            minstop = -1 if self.axis._stop_at_major[1] else 0
            for i in range(minstart, len(major) + minstop):
                maj = major[0] + i * majstep
                minor.extend(np.linspace(maj + minstep, maj + majstep - minstep, minor_num))
            major_frac = (major - offset) / scale
            minor_frac = (np.array(minor) - offset) / scale
            if flip:
                major_frac = 1 - major_frac
                minor_frac = 1 - minor_frac
            use_mask = (major_frac > -0.0001) & (major_frac < 1.0001)
            major_frac = major_frac[use_mask]
            labels = [label for index, label in enumerate(labels) if use_mask[index]]
            minor_frac = minor_frac[(minor_frac > -0.0001) & (minor_frac < 1.0001)]
        elif self.axis.scale_type == "logarithmic":
            domain = np.asarray(self.axis.domain, dtype=float)
            if domain[1] < domain[0]:
                flip = True
                domain = domain[::-1]
            else:
                flip = False
            major, minor, labels = _get_log_ticks(self.axis, self.tick_format_func, domain)
            scale = domain[1] - domain[0]
            major_frac = (major - domain[0]) / scale
            minor_frac = (minor - domain[0]) / scale
            if flip:
                major_frac = 1 - major_frac
                minor_frac = 1 - minor_frac
            use_mask = (major_frac > -0.0001) & (major_frac < 1.0001)
            major_frac = major_frac[use_mask]
            labels = [label for index, label in enumerate(labels) if use_mask[index]]
            minor_frac = minor_frac[(minor_frac > -0.0001) & (minor_frac < 1.0001)]
        elif self.axis.scale_type == "power":
            return NotImplementedError
        return major_frac, minor_frac, labels


vispy.visuals.axis.Ticker = Ticker
