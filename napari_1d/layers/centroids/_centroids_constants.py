"""Line constants"""
from enum import auto

from napari.utils.misc import StringEnum


class Method(StringEnum):
    """Drawing mode"""

    AGG = auto()
    GL = auto()


METHOD_TRANSLATIONS = ["agg", "gl"]
