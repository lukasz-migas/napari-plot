"""Utilities."""

from napari._vispy.utils.visual import (
    create_vispy_layer,
    create_vispy_overlay,
    layer_to_visual,
    overlay_to_visual,
)
from napari.components.overlays import TextOverlay

from napari_plot._vispy.layers.centroids import VispyCentroidsLayer
from napari_plot._vispy.layers.infline import VispyInfLineLayer
from napari_plot._vispy.layers.line import VispyLineLayer
from napari_plot._vispy.layers.multiline import VispyMultiLineLayer
from napari_plot._vispy.layers.region import VispyRegionLayer
from napari_plot._vispy.layers.scatter import VispyScatterLayer
from napari_plot._vispy.overlays.grid_lines import VispyGridLinesOverlay
from napari_plot._vispy.overlays.text import VispyTextOverlay
from napari_plot.components.gridlines import GridLinesOverlay
from napari_plot.layers import Centroids, InfLine, Line, MultiLine, Region, Scatter

layer_to_visual.update(
    {
        Line: VispyLineLayer,
        Centroids: VispyCentroidsLayer,
        Scatter: VispyScatterLayer,
        Region: VispyRegionLayer,
        InfLine: VispyInfLineLayer,
        MultiLine: VispyMultiLineLayer,
    }
)

overlay_to_visual.update(
    {
        TextOverlay: VispyTextOverlay,
        GridLinesOverlay: VispyGridLinesOverlay,
    }
)


__all__ = (
    "create_vispy_layer",
    "create_vispy_overlay",
    "layer_to_visual",
    "overlay_to_visual",
)
