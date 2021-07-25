"""Axis model"""
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import EventedModel
from napari.utils.events.custom_types import Array
from pydantic import validator


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

    @validator("label_color", "tick_color", pre=True)
    def _coerce_color(cls, v):
        return transform_color(v)[0]
