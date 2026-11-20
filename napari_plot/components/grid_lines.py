"""Plot grid lines overlay model."""

from napari.components.overlays.base import CanvasOverlay
from napari.utils.color import ColorValue


class GridLinesOverlay(CanvasOverlay):
    """Grid lines at the major axis ticks.

    Set ``color`` to override the automatic black or white grid color.
    ``None`` picks the color with higher contrast against the canvas background.
    Set ``opacity`` to adjust the visibility of the lines (default 0.25).
    """

    color: ColorValue | None = None
    opacity: float = 0.25
    box: bool = False
