import numpy as np
import pytest
from napari._vispy.utils.qt_font import FontInfo

from napari_plot._vispy.layers.line import VispyLineLayer
from napari_plot.layers import Line


@pytest.mark.parametrize("opacity", [0, 0.3, 0.7, 1])
def test_VispyScatterLayer(opacity):
    points = np.array([[100, 100], [200, 200], [300, 100]])
    layer = Line(points, width=5, opacity=opacity)
    visual = VispyLineLayer(layer, font_info=FontInfo())
    assert visual.node.opacity == opacity
