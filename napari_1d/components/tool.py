"""Tool model."""
from enum import Enum

from napari.utils.events import EventedModel


class InteractiveTool(str, Enum):
    """Interaction mode.

    AUTO : swap between box and span depending on the ranges, similar to the way Plotly does it
    SPAN : infinite region between two values - can be either horizontal or vertical
    BOX : rectangular box
    LASSO : lasso tool allowing selection of data points
    POLYGON : polygon tool allowing selection of data points
    """

    AUTO = "auto"
    SPAN = "span"  # default interaction
    BOX = "box"  # TODO
    LASSO = "lasso"  # TODO
    POLYGON = "polygon"  # TODO


class Tool(EventedModel):
    """Tool model."""

    active: InteractiveTool = InteractiveTool.SPAN
