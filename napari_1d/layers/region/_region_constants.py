"""Region constants"""
from enum import Enum, auto

from napari.utils.misc import StringEnum

from ._region import Horizontal, Vertical


class Mode(StringEnum):
    """
    Mode: Interactive mode. The normal, default mode is PAN_ZOOM

    PAN_ZOOM which allows for normal interactivity with the canvas.
    SELECT allows selecting region(s) by dragging mouse in the canvas
    ADD allows addition of new region
    MOVE allows moving of currently selected regions
    """

    PAN_ZOOM = auto()
    SELECT = auto()
    ADD = auto()
    MOVE = auto()


class Orientation(str, Enum):
    """Orientation"""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


region_classes = {Orientation.HORIZONTAL: Horizontal, Orientation.VERTICAL: Vertical}
