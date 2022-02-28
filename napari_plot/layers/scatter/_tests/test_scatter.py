"""Test scatter layer."""
import numpy as np
import pytest

from napari_plot.layers.scatter import Scatter


def test_scatter_empty():
    layer = Scatter(None)
    assert layer.ndim == 2


@pytest.mark.parametrize("data", ([[0, 1, 2], [1, 2, 3]], np.random.random((10, 2))))
def test_scatter_data(data):
    layer = Scatter(data)
    assert isinstance(layer.data, np.ndarray)


def test_scatter_change_data():
    data = np.random.random((10, 2))
    layer = Scatter(data)

    new_data = np.random.random(10)
    layer.x = new_data
    layer.y = new_data

    data = np.random.random((20, 2))
    layer.data = data
    with pytest.raises(ValueError):
        layer.x = new_data
    with pytest.raises(ValueError):
        layer.y = new_data


def test_centroids_color():
    data = np.random.random((10, 2))
    layer = Scatter(data, face_color="white", edge_color="red")
    np.testing.assert_array_equal(layer.face_color, np.asarray([1.0, 1.0, 1.0, 1.0]))
    np.testing.assert_array_equal(layer.edge_color, np.asarray([1.0, 0.0, 0.0, 1.0]))

    layer.edge_color = np.asarray([1.0, 1.0, 1.0, 1.0])
    np.testing.assert_array_equal(layer.edge_color, np.asarray([1.0, 1.0, 1.0, 1.0]))

    layer.face_color = np.asarray([1.0, 0.0, 0.0, 1.0])
    np.testing.assert_array_equal(layer.face_color, np.asarray([1.0, 0.0, 0.0, 1.0]))
