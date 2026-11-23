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


def test_line_dash_pattern_applies_and_resets() -> None:
    layer = Line([[0, 0], [1, 2], [2, 1]], dashes=(5, 2))
    visual = VispyLineLayer(layer, font_info=FontInfo())
    assert visual.node.method == "agg"
    assert visual.node._line_visual._U["dash_period"] == 7
    layer.dashes = (3, 1, 1, 1)
    assert visual.node._line_visual._U["dash_period"] == 6
    layer.dashes = None
    assert visual.node.method == "gl"
