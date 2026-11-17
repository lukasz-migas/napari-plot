"""Test MultiLine."""

import numpy as np
import pytest

from napari_plot.layers.centroids import Centroids


def test_centroids_empty():
    layer = Centroids(None)
    assert layer.ndim == 2


def test_centroids_default():
    # add no data
    data = None
    layer = Centroids(data)
    assert len(layer.data) == 0

    # add single line
    data = np.random.random((10, 3))
    layer = Centroids(data)
    assert len(layer.data) == 10
    assert layer.orientation == "vertical"


@pytest.mark.parametrize(
    "data",
    [
        np.random.random((10, 2)),
        np.random.random((10, 3)),
    ],
)
@pytest.mark.parametrize("orientation", ["vertical", "horizontal"])
def test_centroids_inputs_multiple(data, orientation):
    layer = Centroids(data, orientation=orientation)
    assert len(layer.data) == 10
    assert layer.orientation == orientation


def test_centroids_change_data():
    data = np.random.random((10, 2))
    layer = Centroids(data)
    np.testing.assert_array_equal(layer.data.shape, (10, 3))
    assert len(layer.color) == 10
    data = np.random.random((15, 3))
    layer.data = data
    np.testing.assert_array_equal(layer.data.shape, (15, 3))
    assert len(layer.color) == 15


def test_centroids_color():
    data = np.random.random((10, 3))
    layer = Centroids(data, color="white")
    np.testing.assert_array_equal(layer.color[0], np.asarray([1.0, 1.0, 1.0, 1.0]))

    layer = Centroids(data, color="red")
    np.testing.assert_array_equal(layer.color[0], np.asarray([1.0, 0.0, 0.0, 1.0]))


def test_centroids_color_change():
    data = np.random.random((10, 3))
    layer = Centroids(data, color="white")
    np.testing.assert_array_equal(layer.color[0], np.asarray([1.0, 1.0, 1.0, 1.0]))

    layer.color = np.full((10, 4), fill_value=(0.0, 1.0, 0.0, 1.0))
    np.testing.assert_array_equal(layer.color[1], np.asarray([0.0, 1.0, 0.0, 1.0]))
    np.testing.assert_array_equal(layer.color[2], np.asarray([0.0, 1.0, 0.0, 1.0]))

    layer.update_color(1, np.array((1.0, 0.0, 1.0, 1.0)))
    np.testing.assert_array_equal(layer.color[1], np.asarray([1.0, 0.0, 1.0, 1.0]))

    data = np.random.random((0, 3))
    layer.data = data
    assert len(layer.color) == len(data)

    data = np.random.random((5, 3))
    layer.data = data
    assert len(layer.color) == len(data)


def test_centroids_x_region_extent_vertical():
    """Region extent spans the start and end of each stick within the window, including signed values."""
    layer = Centroids(np.asarray([[1.0, -3.0], [2.0, 4.0], [3.0, 10.0]]))
    assert layer._get_x_region_extent(0.5, 2.5) == (-3.0, 4.0)
    assert layer._get_x_region_extent(2.0, 3.0) == (0.0, 10.0)
    assert layer._get_x_region_extent(5.0, 6.0) == (None, None)


def test_centroids_x_region_extent_horizontal():
    """Horizontal centroids report the y-position of sticks crossing the window."""
    layer = Centroids(np.asarray([[1.0, 0.0, 5.0], [2.0, 0.0, 1.0], [3.0, 4.0, 8.0]]), orientation="horizontal")
    assert layer._get_x_region_extent(2.0, 3.0) == (1.0, 1.0)
    assert layer._get_x_region_extent(4.5, 6.0) == (1.0, 3.0)
    assert layer._get_x_region_extent(9.0, 10.0) == (None, None)
