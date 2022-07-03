"""Test plotting API."""
import numpy as np

from napari_plot.components.viewer_model import ViewerModel


def test_plot():
    """Test line API."""
    x = np.arange(10, 20)
    y = np.arange(10, 20)
    viewer = ViewerModel()

    # only specify y-axis
    layer = viewer.plot(y)
    assert layer.data[0, 0] == 0
    # specify x/y-axis
    layer = viewer.plot(x, y)
    assert layer.data[0, 0] == 10

    # specify x/y-axis + color
    layer = viewer.plot(x, y, "r")
    np.testing.assert_array_equal(layer.color, (1.0, 0.0, 0.0, 1.0))

    # specify x/y-axis + color + as scatter
    layer = viewer.plot(x, y, "ro")
    np.testing.assert_array_equal(layer.face_color[-1], (1.0, 0.0, 0.0, 1.0))
    assert layer.symbol == "disc"


def test_scatter():
    """Test scatter API."""
    x = np.arange(10, 20)
    y = np.arange(10, 20)
    viewer = ViewerModel()
    # add scatter with uniform size
    layer = viewer.scatter(x, y, s=10)
    assert layer.size[0] == 10
    # add scatter with varying size
    layer = viewer.scatter(x, y, s=np.arange(1, 11))
    assert layer.size[-1] == 10
