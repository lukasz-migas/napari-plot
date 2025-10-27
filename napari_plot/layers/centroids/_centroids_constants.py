"""Line constants"""

from enum import auto

from napari.utils.compat import StrEnum
from napari.utils.misc import StringEnum


class Method(StringEnum):
    """Drawing mode"""

    AGG = auto()
    GL = auto()


METHOD_TRANSLATIONS = ["agg", "gl"]


class ColoringType(StringEnum):
    """Type of coloring."""

    SINGLE = auto()
    SELECTION = auto()
    ALL = auto()


COLORING_TRANSLATIONS = ["single", "all"]


class Orientation(StrEnum):
    """Orientation"""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
