"""Plot grid lines overlay model."""

from napari.components.overlays.base import CanvasOverlay
from napari.utils.color import ColorValue
from pydantic import Field


class GridLinesOverlay(CanvasOverlay):
    """Grid lines at the major axis ticks.

    The lines are drawn in every plot cell when the canvas grid mode is enabled.

    Attributes
    ----------
    color : ColorValue or None
        Color of the grid lines, or None to pick black or white automatically, whichever has the higher contrast
        against the canvas background.
    width : float
        Width of the grid lines, in screen pixels.
    minor : bool
        Whether to also draw lines at the minor tick positions.
    visible : bool
        If the grid lines are visible or not.
    opacity : float
        The opacity of the grid lines. 0 is fully transparent.
    """

    color: ColorValue | None = None
    width: float = Field(default=0.5, gt=0)
    opacity: float = 0.25
    box: bool = False
    gridded: bool = True
    minor: bool = False
