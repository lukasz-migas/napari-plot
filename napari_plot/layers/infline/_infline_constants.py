"""Region constants"""
from enum import Enum, auto

from napari.utils.misc import StringEnum


class Mode(StringEnum):
    """
    Mode: Interactive mode. The normal, default mode is PAN_ZOOM

    PAN_ZOOM which allows for normal interactivity with the canvas.

    SELECT allows selection of new window

    MOVE allows moving of the current window

    ADD allows adding new line
    """

    PAN_ZOOM = auto()
    TRANSFORM = auto()
    ADD = auto()
    MOVE = auto()
    SELECT = auto()


class Box:
    """Box: Constants associated with the vertices of the interaction box"""

    WITH_HANDLE = [0, 1, 2, 3, 4, 5, 6, 7]
    LINE_HANDLE = [7, 6, 4, 2, 0, 7]
    LINE = [0, 2, 4, 6, 0]
    TOP_LEFT = 0
    TOP_CENTER = 7
    LEFT_CENTER = 1
    BOTTOM_RIGHT = 4
    BOTTOM_LEFT = 2
    CENTER = 8
    LEN = 8


class Orientation(str, Enum):
    """Orientation"""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
