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
    CATEGORICAL = "categorical"


def transform_axis_values(
    values: ty.Any,
    scale: AxisScale | str,
    *,
    inverse: bool = False,
) -> ty.Any:
    """Transform values between data and displayed axis coordinates."""
    scale = AxisScale(scale)
    if scale is not AxisScale.LOG:
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
    x_categories: tuple[str, ...] | None = None
    y_categories: tuple[str, ...] | None = None

    def __init__(self, **data: ty.Any) -> None:
        """Initialize the axis and synchronize categorical scale fields."""
        for name in ("x", "y"):
            categories = data.get(f"{name}_categories")
            scale_name = f"{name}_scale"
            scale = AxisScale(data.get(scale_name, AxisScale.LINEAR))
            if categories is not None:
                data[scale_name] = AxisScale.CATEGORICAL
            elif scale is AxisScale.CATEGORICAL:
                raise ValueError(f"{name}_categories must be provided for a categorical axis.")
        super().__init__(**data)

    def __setattr__(self, name: str, value: ty.Any) -> None:
        """Keep each categorical label sequence synchronized with its scale."""
        if name in {"x_categories", "y_categories"}:
            axis_name = name[0]
            scale_name = f"{axis_name}_scale"
            super().__setattr__(name, value)
            categories = getattr(self, name)
            current_scale = getattr(self, scale_name)
            if categories is not None:
                super().__setattr__(scale_name, AxisScale.CATEGORICAL)
            elif current_scale is AxisScale.CATEGORICAL:
                super().__setattr__(scale_name, AxisScale.LINEAR)
            return

        if name in {"x_scale", "y_scale"}:
            scale = AxisScale(value)
            categories_name = f"{name[0]}_categories"
            categories = getattr(self, categories_name, None)
            if scale is AxisScale.CATEGORICAL and categories is None:
                raise ValueError(f"{categories_name} must be provided for a categorical axis.")
            if scale is not AxisScale.CATEGORICAL and categories is not None:
                super().__setattr__(categories_name, None)
            super().__setattr__(name, scale)
            return

        super().__setattr__(name, value)

    @field_validator("label_color", "tick_color", mode="before")
    @classmethod
    def _coerce_color(cls, v):
        return transform_color(v)[0]

    @field_validator("x_categories", "y_categories", mode="before")
    @classmethod
    def _coerce_categories(
        cls,
        value: ty.Iterable[str] | None,
    ) -> tuple[str, ...] | None:
        """Validate and freeze an ordered sequence of category labels."""
        if value is None:
            return None
        if isinstance(value, str):
            raise TypeError("Categories must be provided as a sequence of strings.")
        categories = tuple(value)
        if not categories:
            raise ValueError("Categories must contain at least one label.")
        if not all(isinstance(label, str) for label in categories):
            raise TypeError("Category labels must be strings.")
        return categories
