import numpy as np
import pytest

from napari_plot._vispy.layers.scatter import VispyScatterLayer
from napari_plot.layers import Scatter


@pytest.mark.parametrize("opacity", [0, 0.3, 0.7, 1])
def test_VispyScatterLayer(opacity):
    points = np.array([[100, 100], [200, 200], [300, 100]])
    layer = Scatter(points, size=30, opacity=opacity)
    visual = VispyScatterLayer(layer)
    assert visual.node.opacity == opacity
