"""Line constants"""
from enum import Enum, auto

from napari.utils.misc import StringEnum


class Method(StringEnum):
    """Drawing mode"""

    AGG = auto()
    GL = auto()


METHOD_TRANSLATIONS = ["agg", "gl"]


class Orientation(str, Enum):
    """Orientation"""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
