"""Utilities."""
from napari._vispy.layers.base import VispyBaseLayer
from napari._vispy.layers.points import VispyPointsLayer
from napari._vispy.layers.shapes import VispyShapesLayer
from napari.layers import Points, Shapes

from ...layers import Centroids, InfLine, Line, Region, Scatter
from ..layers.centroids import VispyCentroidsLayer
from ..layers.infline import VispyInfLineLayer
from ..layers.line import VispyLineLayer
from ..layers.region import VispyRegionLayer
from ..layers.scatter import VispyScatterLayer

layer_to_visual = {
    Line: VispyLineLayer,
    Centroids: VispyCentroidsLayer,
    Scatter: VispyScatterLayer,
    Shapes: VispyShapesLayer,
    Points: VispyPointsLayer,
    Region: VispyRegionLayer,
    InfLine: VispyInfLineLayer,
}


def create_vispy_visual(layer) -> VispyBaseLayer:
    """Create vispy visual for a layer based on its layer type.

    Parameters
    ----------
    layer : napari.layers._base_layer.Layer
        Layer that needs its property widget created.

    Returns
    -------
    visual : vispy.scene.visuals.VisualNode
        Vispy visual node
    """
    for layer_type, visual_class in layer_to_visual.items():
        if isinstance(layer, layer_type):
            return visual_class(layer)

    raise TypeError(f"Could not find VispyLayer for layer of type {type(layer)}")
