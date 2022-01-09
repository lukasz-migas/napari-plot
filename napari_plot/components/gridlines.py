"""Gridlines"""
from napari.utils.events import EventedModel


class GridLines(EventedModel):
    """Gridlines object"""

    visible: bool = False
