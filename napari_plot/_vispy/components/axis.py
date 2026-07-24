"""Reimplementation of axis-visual"""

from __future__ import annotations

import inspect
import typing as ty

import numpy as np
import vispy.visuals.axis
from vispy.visuals.axis import Ticker as _Ticker, _get_ticks_talbot

default_tick_formatter = lambda x: "%g" % x  # noqa


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
    tick_spacing: float,
) -> list[str]:
    """Format tick values, providing spacing to formatters that request it."""
    if _accepts_tick_spacing(formatter):
        return [formatter(float(value), tick_spacing=tick_spacing) for value in values]
    return [formatter(float(value)) for value in values]


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

            major = _get_ticks_talbot(domain[0], domain[1], n_inches, 2)
            majstep = major[1] - major[0]
            labels = _format_ticks(self.tick_format_func, major, float(abs(majstep)))
            minor = []
            minstep = majstep / (minor_num + 1)
            minstart = 0 if self.axis._stop_at_major[0] else -1
            minstop = -1 if self.axis._stop_at_major[1] else 0
            for i in range(minstart, len(major) + minstop):
                maj = major[0] + i * majstep
                minor.extend(np.linspace(maj + minstep, maj + majstep - minstep, minor_num))
            major_frac = (major - offset) / scale
            minor_frac = (np.array(minor) - offset) / scale
            major_frac = major_frac[::-1] if flip else major_frac
            use_mask = (major_frac > -0.0001) & (major_frac < 1.0001)
            major_frac = major_frac[use_mask]
            labels = [label for index, label in enumerate(labels) if use_mask[index]]
            minor_frac = minor_frac[(minor_frac > -0.0001) & (minor_frac < 1.0001)]
        elif self.axis.scale_type == "logarithmic" or self.axis.scale_type == "power":
            return NotImplementedError
        return major_frac, minor_frac, labels


vispy.visuals.axis.Ticker = Ticker
