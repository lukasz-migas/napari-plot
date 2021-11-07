"""Utils"""
import numpy as np
from napari._vispy.layers.base import VispyBaseLayer
from napari._vispy.layers.points import VispyPointsLayer
from napari._vispy.layers.shapes import VispyShapesLayer

from ..layers import Centroids, InfLine, Line, Points, Region, Scatter, Shapes
from .vispy_centroids_layer import VispyCentroidsLayer
from .vispy_infline_layer import VispyInfLineLayer
from .vispy_line_layer import VispyLineLayer
from .vispy_region_layer import VispyRegionLayer
from .vispy_scatter_layer import VispyScatterLayer

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


def tick_formatter(value: float) -> str:
    """Format tick value"""
    value = float(value)
    exp_value = np.round(np.log10(abs(value)))
    if np.isinf(exp_value):
        exp_value = 1
    if exp_value < 3:
        if abs(value) <= 1:
            return f"{value:.2G}"
        elif abs(value) <= 1e3:
            if value.is_integer():
                return f"{value:.0F}"
            return f"{value:.1F}"
    elif exp_value < 6:
        return f"{value / 1e3:.1f}k"
    elif exp_value < 9:
        return f"{value / 1e6:.1f}M"
    elif exp_value < 12:
        return f"{value / 1e9:.1f}B"
    elif exp_value < 16:
        return f"{value / 1e12:.1f}T"
