"""Vispy."""

from napari._vispy.utils.visual import overlay_to_visual

from napari_plot._vispy.overlays.grid_lines import VispyGridLinesOverlay
from napari_plot.components.grid_lines import GridLinesOverlay


def register_vispy_overlays():
    """Register vispy overlays."""
    overlay_to_visual.update(
        {
            GridLinesOverlay: VispyGridLinesOverlay,
        }
    )
