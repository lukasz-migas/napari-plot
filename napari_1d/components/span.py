"""Region model"""
from enum import Enum
from typing import Tuple

from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import EventedModel
from napari.utils.events.custom_types import Array
from pydantic import validator


class Orientation(Enum):
    """Orientation of the span"""

    HORIZONTAL = 0
    VERTICAL = 1


class Span(EventedModel):
    """Span"""

    visible: bool = False
    color: Array[float, (4,)] = (1.0, 1.0, 1.0, 1.0)
    opacity: float = 0.3
    position: Tuple[float, float] = (0, 0)
    orientation: Orientation = Orientation.VERTICAL

    @validator("color", pre=True)
    def _coerce_color(cls, v):
        return transform_color(v)[0]
