"""Legend model."""
import typing as ty

import numpy as np
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import EventedModel
from napari.utils.events.custom_types import Array
from pydantic import Field, validator

from ._constants import LegendPosition


class Legend(EventedModel):
    """Legend displaying layer information

    Attributes
    ----------
    visible : bool
        If legend is visible or not.
    color : np.ndarray
        A (4,) color array of the legend text.
    font_size : float
        The font size (in points) of the text.
    position : str
        Position of the legend in the canvas. Must be one of 'top left', 'top right', 'top center', 'bottom right',
        'bottom left', 'bottom_center'.
        Default value is 'top left'
    border: bool
        If legend should have border around it.
    border_color : np.ndarray
        A (4,) color array of the legend border.
    """

    # fields
    visible: bool = False
    title: str = ""
    color: Array[float, (4,)] = (0.5, 0.5, 0.5, 1.0)
    font_size: float = 10
    bold: bool = False
    border: bool = False
    border_color: Array[float, (4,)] = (0.5, 0.5, 0.5, 1.0)
    position: LegendPosition = LegendPosition.TOP_LEFT
    handles: ty.List[ty.Tuple[str, Array[float, (4,)]]] = Field(default_factory=list)

    @validator("color", "border_color", pre=True)
    def _coerce_color(cls, v):
        return transform_color(v)[0]

    @property
    def text(self) -> ty.List[str]:
        """Return text."""
        text = [v[0] for v in self.handles]
        if self.title:
            text.insert(0, self.title)
        return text

    @property
    def text_color(self):
        """Return text color."""
        if len(self.handles) == 0:
            return np.zeros((4,))
        colors = [v[1] for v in self.handles]
        if self.title:
            colors.insert(0, self.color)
        return np.vstack(colors)
