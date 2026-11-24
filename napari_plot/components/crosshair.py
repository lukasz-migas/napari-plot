"""Crosshair overlay model."""

from napari.components.overlays.base import CanvasOverlay
from napari.utils.color import ColorValue


class CrosshairOverlay(CanvasOverlay):
    """Horizontal and vertical lines through the cursor, with an optional coordinate label.

    The overlay is hidden by default. ``snap_to_data`` moves the lines to the data point under the cursor instead of
    following it freely; they always snap while the hover readout is visible. ``color`` set to ``None`` follows the
    axis color. ``point`` is the data position the lines go through, updated by the viewer, or ``None`` to hide them.
    """

    visible: bool = False
    gridded: bool = True
    color: ColorValue | None = None
    width: float = 1.0
    opacity: float = 0.6
    snap_to_data: bool = False
    show_coordinates: bool = True
    point: tuple[float, float] | None = None
