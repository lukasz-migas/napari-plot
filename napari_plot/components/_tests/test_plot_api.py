"""Test plotting API."""
import numpy as np
import pytest

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


@pytest.mark.parametrize("align", ("center", "edge"))
def test_bar(align):
    """Test bar/barh API."""
    x = np.arange(0, 10)
    y1 = np.arange(10, 20)
    y2 = np.random.randint(0, 100, 10)

    viewer = ViewerModel()
    # add vertical barchart
    layer, _ = viewer.bar(x, y1, align=align)
    assert len(layer.data) == 10
    layer, _ = viewer.bar(x, y1, bottom=y2, align=align)

    # add horizontal barchart
    layer, _ = viewer.barh(x, y1, align=align)
    layer, _ = viewer.barh(x, y1, left=y2, align=align)


def test_nan_bar_values():
    viewer = ViewerModel()
    viewer.bar([0, 1], [np.nan, 4])


def test_bar_ticklabel_fail():
    viewer = ViewerModel()
    with pytest.raises(IndexError):
        viewer.bar([], [])


def test_axlines():
    """Test axvline/axhline."""
    viewer = ViewerModel()
    # add vertical line
    layer = viewer.axvline()
    assert layer.data[0] == 0
    assert layer.orientation[0] == "vertical"
    layer = viewer.axvline(50)
    assert layer.data[0] == 50

    # add horizontal line
    layer = viewer.axhline()
    assert layer.orientation[0] == "horizontal"
    assert layer.data[0] == 0
    layer = viewer.axhline(50)
    assert layer.data[0] == 50


def test_axspan():
    """Test axvline/axhline."""
    viewer = ViewerModel()
    # add vertical line
    layer = viewer.axvspan(0, 100)
    assert layer.orientation[0] == "vertical"

    # add horizontal line
    layer = viewer.axhspan(50, 551)
    assert layer.orientation[0] == "horizontal"


def test_hist():
    """Test hist API."""
    # make data
    x1 = np.random.normal(0, 0.8, 100)

    viewer = ViewerModel()
    _, _, layers = viewer.hist(x1, alpha=0.3)
    assert len(layers) == 1
    assert layers[0].opacity == 0.3


def test_length_one_hist():
    viewer = ViewerModel()
    viewer.hist(1)
    viewer.hist([1])


def test_hist2d():
    """Test hist2d API."""
    # make data
    x = np.random.normal(size=500)
    y = x * 3 + np.random.normal(size=500)

    viewer = ViewerModel()
    viewer.hist2d(x)
