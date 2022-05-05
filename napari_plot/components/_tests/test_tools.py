import numpy as np

from napari_plot.components.tools import PolygonTool


def test_polygon_lasso():
    tool = PolygonTool()

    tool.add_point((0, 0))
    assert len(tool.data) == 1
    tool.add_point((0, 0))  # same point is not added twice
    assert len(tool.data) == 1
    tool.add_point((2, 3))
    tool.add_point((4, 3))

    tool.remove_point(-1)  # remove last
    assert len(tool.data) == 2

    assert np.all(tool.data[0] == (0, 0))
    tool.remove_nearby_point((0, 0))
    assert np.all(tool.data[0] != (0, 0))

    tool.clear()
    assert len(tool.data) == 0
