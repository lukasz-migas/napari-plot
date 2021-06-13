"""Line constants"""
# Standard library imports
from enum import auto

# Third-party imports
from napari.utils.misc import StringEnum


class Method(StringEnum):
    """Drawing mode"""

    AGG = auto()
    GL = auto()


METHOD_TRANSLATIONS = ["agg", "gl"]
