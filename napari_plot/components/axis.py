"""Axis model"""

from __future__ import annotations

import textwrap
import typing as ty
from datetime import UTC, date, datetime, time
from enum import StrEnum

import numpy as np
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import EventedModel
from napari.utils.events.custom_types import Array
from napari.utils.theme import get_theme
from pydantic import Field, field_validator


class AxisScale(StrEnum):
    """Supported axis scales."""

    LINEAR = "linear"
    LOG = "log"
    CATEGORICAL = "categorical"
    POWER = "power"
    DATETIME = "datetime"


class TickNotation(StrEnum):
    """Number formatting for numeric axis ticks."""

    DEFAULT = "default"
    SCIENTIFIC = "scientific"
    OFFSET = "offset"


UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def transform_axis_values(
    values: ty.Any,
    scale: AxisScale | str,
    *,
    inverse: bool = False,
    power: float = 2.0,
) -> ty.Any:
    """Transform values between data and displayed axis coordinates."""
    scale = AxisScale(scale)
    if scale not in (AxisScale.LOG, AxisScale.POWER):
        return values

    array = np.asarray(values, dtype=float)
    if scale is AxisScale.POWER:
        transformed = np.sign(array) * np.power(np.abs(array), 1 / power if inverse else power)
    elif inverse:
        with np.errstate(over="ignore", invalid="ignore"):
            transformed = np.power(10.0, array)
    else:
        if np.any(array <= 0):
            raise ValueError("Logarithmic axis values must be positive.")
        transformed = np.log10(array)
    if np.isscalar(values):
        return float(transformed)
    return transformed


def datetime_axis_values(values: ty.Any, *, origin: date | datetime = UNIX_EPOCH) -> np.ndarray:
    """Convert datetimes to seconds relative to an axis's configured datetime origin.

    Naive datetimes are interpreted as UTC. Use a nearby origin to preserve precision for short intervals.
    """
    if isinstance(origin, datetime) and origin.tzinfo is not None:
        origin = origin.astimezone(UTC).replace(tzinfo=None)
    array = np.asarray(values)
    if array.dtype.kind == "O":
        array = np.asarray(
            [
                value.astimezone(UTC).replace(tzinfo=None)
                if isinstance(value, datetime) and value.tzinfo is not None
                else value
                for value in array.flat
            ],
            dtype="datetime64[us]",
        ).reshape(array.shape)
    delta = array.astype("datetime64[us]") - np.datetime64(origin, "us")
    return delta / np.timedelta64(1, "s")


def wrap_label(label: str, width: int = 12) -> str:
    """Break a category label on spaces into lines of at most ``width`` characters (long words are kept whole).

    Use it as an axis category formatter, e.g. ``viewer.axis.y_category_formatter = wrap_label``.
    """
    return "\n".join(textwrap.wrap(label, width=width, break_long_words=False, break_on_hyphens=False)) or label


class Axis(EventedModel):
    """Axis model.

    ``x_category_formatter`` / ``y_category_formatter`` map each categorical tick label to the displayed text
    (e.g. :func:`wrap_label` to put words on separate lines); the categories themselves are unchanged.

    ``x_tick_rotation`` turns the x tick labels counter-clockwise by that many degrees (like matplotlib's
    ``rotation``), with each label ending at its tick; the axis grows to fit angled category labels.
    ``x_thin_categories`` / ``y_thin_categories`` hide overlapping category labels; turn them off to always show every
    label (e.g. on a heatmap).

    Axis inversion changes display order while camera bounds stay in increasing data order. ``x_datetime_origin``
    and ``y_datetime_origin`` define the zero point for numeric seconds on a datetime axis. ``x_power`` and ``y_power``
    set the exponents for the sign-preserving power scale.
    """

    visible: bool = True
    x_label: str = "X-label"
    y_label: str = "Y-label"
    label_size: float = 10
    label_color: Array[float, (4,)] | None = None
    tick_size: float = 8
    tick_color: Array[float, (4,)] | None = None
    x_label_margin: int = 30
    y_label_margin: int = 80
    x_tick_margin: int = 20
    y_tick_margin: int = 10
    x_max_size: int = 60
    y_max_size: int = 120
    x_tick_formatter: ty.Callable[..., str] | None = None
    y_tick_formatter: ty.Callable[..., str] | None = None
    x_scale: AxisScale = AxisScale.LINEAR
    y_scale: AxisScale = AxisScale.LINEAR
    x_inverted: bool = False
    y_inverted: bool = False
    x_minor_ticks: bool = True
    y_minor_ticks: bool = True
    x_tick_notation: TickNotation = TickNotation.DEFAULT
    y_tick_notation: TickNotation = TickNotation.DEFAULT
    x_power: float = Field(2.0, gt=0, allow_inf_nan=False)
    y_power: float = Field(2.0, gt=0, allow_inf_nan=False)
    x_datetime_origin: datetime = UNIX_EPOCH
    y_datetime_origin: datetime = UNIX_EPOCH
    x_categories: tuple[str, ...] | None = None
    y_categories: tuple[str, ...] | None = None
    x_category_formatter: ty.Callable[[str], str] | None = None
    y_category_formatter: ty.Callable[[str], str] | None = None
    x_tick_rotation: float = 0.0
    x_thin_categories: bool = True
    y_thin_categories: bool = True

    @field_validator("x_datetime_origin", "y_datetime_origin", mode="before")
    @classmethod
    def _coerce_datetime_origin(cls, value: ty.Any) -> ty.Any:
        if isinstance(value, date) and not isinstance(value, datetime):
            value = datetime.combine(value, time.min)
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

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
    def _coerce_color(cls, value: ty.Any) -> np.ndarray | None:
        return None if value is None else transform_color(value)[0]

    def colors_for_theme(self, theme: str) -> tuple[np.ndarray, np.ndarray]:
        """Return tick and label colors, using the theme for unset colors."""
        tick_color, label_color = self.tick_color, self.label_color
        if tick_color is None or label_color is None:
            default = transform_color(get_theme(theme).text.as_hex())[0]
            tick_color = default if tick_color is None else tick_color
            label_color = default if label_color is None else label_color
        return tick_color, label_color

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
