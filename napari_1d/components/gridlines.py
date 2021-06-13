"""Gridlines"""
from napari.utils.events import EventedModel


class GridLines(EventedModel):
    """Gridlines object"""

    # fields
    visible: bool = False
