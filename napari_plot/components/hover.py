"""Hover readout overlay model."""

from collections.abc import Callable

from napari.components._viewer_constants import CanvasPosition
from napari.components.overlays.text import TextOverlay

from napari_plot.utils.hover import HoverInfo


class HoverOverlay(TextOverlay):
    """Text box describing the data point under the cursor.

    The overlay is hidden by default; when visible, the crosshair (if shown) also snaps to the data. ``text`` is set by
    the viewer as the cursor moves and is empty when no data is under the cursor, which hides the box. Set
    ``formatter`` to a function of :class:`~napari_plot.utils.hover.HoverInfo` to change the text. ``box_padding`` sets
    the horizontal and vertical padding of the box in pixels (``None`` uses the canvas default).
    """

    visible: bool = False
    position: CanvasPosition = CanvasPosition.TOP_RIGHT
    box: bool = True
    formatter: Callable[[HoverInfo], str] | None = None
    box_padding: tuple[int, int] | None = None
