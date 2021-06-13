"""Axis model"""
from napari.utils.events import EventedModel


class Axis(EventedModel):
    """Axis"""

    visible: bool = True
    x_label: str = "x-axis"
    y_label: str = "y-label"
    label_size: float = 10
    label_color: str = "#FFFFFF"
    tick_size: float = 8
    tick_color: str = "#FFFFFF"
    x_label_margin: int = 30
    y_label_margin: int = 80
    x_tick_margin: int = 20
    y_tick_margin: int = 10
    x_max_size: int = 60
    y_max_size: int = 120
