"""Utilities."""

import napari._vispy.utils.visual
from napari._vispy.utils.visual import create_vispy_layer, create_vispy_overlay
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

layer_to_visual = {
    Line: VispyLineLayer,
    Centroids: VispyCentroidsLayer,
    Scatter: VispyScatterLayer,
    Region: VispyRegionLayer,
    InfLine: VispyInfLineLayer,
    MultiLine: VispyMultiLineLayer,
}
layer_to_visual.update(napari._vispy.utils.visual.layer_to_visual)
napari._vispy.utils.visual.layer_to_visual = layer_to_visual
# napari._vispy.utils.visual.layer_to_visual.update(layer_to_visual)

overlay_to_visual = {
    TextOverlay: VispyTextOverlay,
    GridLinesOverlay: VispyGridLinesOverlay,
}
napari._vispy.utils.visual.overlay_to_visual.update(overlay_to_visual)


__all__ = (
    "create_vispy_layer",
    "create_vispy_overlay",
    "layer_to_visual",
    "overlay_to_visual",
)
