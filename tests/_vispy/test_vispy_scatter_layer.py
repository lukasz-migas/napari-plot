import numpy as np
import pytest
from napari._vispy.utils.qt_font import FontInfo

from napari_plot._vispy.layers.scatter import VispyScatterLayer
from napari_plot.layers import Scatter


@pytest.mark.parametrize("opacity", [0, 0.3, 0.7, 1])
def test_VispyScatterLayer(opacity):
    points = np.array([[100, 100], [200, 200], [300, 100]])
    layer = Scatter(points, size=30, opacity=opacity)
    visual = VispyScatterLayer(layer, font_info=FontInfo())
    assert visual.node.opacity == opacity


def test_vispy_scatter_node_scaling_follows_layer() -> None:
    """Markers render in pixels by default and in data units when the layer scales with zoom."""
    layer = Scatter(np.array([[0, 0], [1, 1]]))
    visual = VispyScatterLayer(layer, font_info=FontInfo())
    assert visual.node.points_markers.scaling == "fixed"
    layer.scaling = True
    assert visual.node.points_markers.scaling == "visual"
    layer.scaling = False
    assert visual.node.points_markers.scaling == "fixed"
