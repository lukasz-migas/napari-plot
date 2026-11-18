"""Utilities."""

import napari._vispy.utils.visual
from napari._vispy.utils.visual import create_vispy_layer, create_vispy_overlay
from napari.components.overlays import TextOverlay

from napari_plot._vispy.layers.areas import VispyAreasLayer
from napari_plot._vispy.layers.band import VispyBandLayer
from napari_plot._vispy.layers.bar import VispyBarLayer
from napari_plot._vispy.layers.centroids import VispyCentroidsLayer
from napari_plot._vispy.layers.error_bar import VispyErrorBarLayer
from napari_plot._vispy.layers.infline import VispyInfLineLayer
from napari_plot._vispy.layers.line import VispyLineLayer
from napari_plot._vispy.layers.multiline import VispyMultiLineLayer
from napari_plot._vispy.layers.rectangles import VispyRectanglesLayer
from napari_plot._vispy.layers.region import VispyRegionLayer
from napari_plot._vispy.layers.scatter import VispyScatterLayer
from napari_plot._vispy.layers.text import VispyTextLayer
from napari_plot._vispy.overlays.grid_lines import VispyGridLinesOverlay
from napari_plot._vispy.overlays.text import VispyTextOverlay
from napari_plot.components.grid_lines import GridLinesOverlay
from napari_plot.layers import (
    Areas,
    Band,
    Bar,
    Centroids,
    ErrorBar,
    InfLine,
    Line,
    MultiLine,
    Rectangles,
    Region,
    Scatter,
    Text,
)

layer_to_visual = {
    Areas: VispyAreasLayer,
    Band: VispyBandLayer,
    Bar: VispyBarLayer,
    ErrorBar: VispyErrorBarLayer,
    Line: VispyLineLayer,
    Centroids: VispyCentroidsLayer,
    Scatter: VispyScatterLayer,
    Rectangles: VispyRectanglesLayer,
    Region: VispyRegionLayer,
    InfLine: VispyInfLineLayer,
    MultiLine: VispyMultiLineLayer,
    Text: VispyTextLayer,
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
