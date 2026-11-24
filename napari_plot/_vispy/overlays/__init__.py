"""Vispy."""

from napari._vispy.utils.visual import overlay_to_visual

from napari_plot._vispy.overlays.crosshair import VispyCrosshairOverlay
from napari_plot._vispy.overlays.grid_lines import VispyGridLinesOverlay
from napari_plot._vispy.overlays.hover import VispyHoverOverlay
from napari_plot._vispy.overlays.legend import VispyLegendOverlay
from napari_plot.components.crosshair import CrosshairOverlay
from napari_plot.components.grid_lines import GridLinesOverlay
from napari_plot.components.hover import HoverOverlay
from napari_plot.components.legend import LegendOverlay


def register_vispy_overlays() -> None:
    """Register vispy overlays."""
    overlay_to_visual.update(
        {
            CrosshairOverlay: VispyCrosshairOverlay,
            GridLinesOverlay: VispyGridLinesOverlay,
            HoverOverlay: VispyHoverOverlay,
            LegendOverlay: VispyLegendOverlay,
        }
    )
