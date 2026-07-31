"""Axis model"""

from __future__ import annotations

import typing as ty
from enum import StrEnum

import numpy as np
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import EventedModel
from napari.utils.events.custom_types import Array
from pydantic import field_validator


class AxisScale(StrEnum):
    """Supported axis scales."""

    LINEAR = "linear"
    LOG = "log"


def transform_axis_values(
    values: ty.Any,
    scale: AxisScale | str,
    *,
    inverse: bool = False,
) -> ty.Any:
    """Transform values between data and displayed axis coordinates."""
    scale = AxisScale(scale)
    if scale is AxisScale.LINEAR:
        return values

    array = np.asarray(values, dtype=float)
    if inverse:
        with np.errstate(over="ignore", invalid="ignore"):
            transformed = np.power(10.0, array)
    else:
        if np.any(array <= 0):
            raise ValueError("Logarithmic axis values must be positive.")
        transformed = np.log10(array)
    if np.isscalar(values):
        return float(transformed)
    return transformed


class Axis(EventedModel):
    """Axis model."""

    visible: bool = True
    x_label: str = "X-label"
    y_label: str = "Y-label"
    label_size: float = 10
    label_color: Array[float, (4,)] = (1.0, 1.0, 1.0, 1.0)
    tick_size: float = 8
    tick_color: Array[float, (4,)] = (1.0, 1.0, 1.0, 1.0)
    x_label_margin: int = 30
    y_label_margin: int = 80
    x_tick_margin: int = 20
    y_tick_margin: int = 10
    x_max_size: int = 60
    y_max_size: int = 120
    x_tick_formatter: ty.Callable | None = None
    y_tick_formatter: ty.Callable | None = None
    x_scale: AxisScale = AxisScale.LINEAR
    y_scale: AxisScale = AxisScale.LINEAR

    @field_validator("label_color", "tick_color", mode="before")
    @classmethod
    def _coerce_color(cls, v):
        return transform_color(v)[0]
