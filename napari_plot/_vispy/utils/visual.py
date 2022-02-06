"""Utilities."""
from napari._vispy.layers.base import VispyBaseLayer
from napari._vispy.layers.image import VispyImageLayer
from napari._vispy.layers.points import VispyPointsLayer
from napari._vispy.layers.shapes import VispyShapesLayer
from napari.layers import Points, Shapes

from ...layers import Centroids, Image, InfLine, Line, MultiLine, Region, Scatter
from ..layers.centroids import VispyCentroidsLayer
from ..layers.infline import VispyInfLineLayer
from ..layers.line import VispyLineLayer
from ..layers.multiline import VispyMultiLineLayer
from ..layers.region import VispyRegionLayer
from ..layers.scatter import VispyScatterLayer

layer_to_visual = {
    # napari-plot layers
    Line: VispyLineLayer,
    Centroids: VispyCentroidsLayer,
    Scatter: VispyScatterLayer,
    Region: VispyRegionLayer,
    InfLine: VispyInfLineLayer,
    MultiLine: VispyMultiLineLayer,
    # napari layers
    Shapes: VispyShapesLayer,
    Points: VispyPointsLayer,
    Image: VispyImageLayer,
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
