"""Region model"""
from typing import Tuple

from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import EventedModel
from napari.utils.events.custom_types import Array
from pydantic import validator


class BoxZoom(EventedModel):
    """BoxZoom model"""

    visible: bool = False
    color: Array[float, (4,)] = (0.0, 1.0, 0.0, 1.0)
    opacity: float = 0.3
    rect: Tuple[float, ...] = (0, 0, 0, 0)

    @validator("color", pre=True)
    def _coerce_color(cls, v):
        return transform_color(v)[0]
