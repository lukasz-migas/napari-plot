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

    # try updating with wrongly shaped data
    new_data = np.random.random(15)
    with pytest.raises(ValueError):
        layer.x = new_data
    with pytest.raises(ValueError):
        layer.y = new_data

    data = np.random.random((20, 2))
    layer.data = data

    # try updating with 2d data when 1d data is expected
    with pytest.raises(ValueError):
        layer.x = new_data
    with pytest.raises(ValueError):
        layer.y = new_data

    # set 0-sized array
    data = np.zeros((0, 2))
    layer.data = data
    assert layer.edge_width.shape[0] == 0
    assert layer.edge_color.shape[0] == 0
    assert layer.face_color.shape[0] == 0
    assert layer.size.shape[0] == 0

    # and then N sized array
    data = np.zeros((100, 2))
    layer.data = data
    assert layer.edge_width.shape[0] == 100
    assert layer.edge_color.shape[0] == 100
    assert layer.face_color.shape[0] == 100
    assert layer.size.shape[0] == 100


def test_scatter_edge_width():
    data = np.random.random((10, 2))
    layer = Scatter(data, edge_width=4, edge_width_is_relative=False)
    layer.edge_width = 3
    assert np.all(layer.edge_width == 3)
    layer.edge_width = np.arange(len(data))
    assert layer.edge_width[0] == 0
    assert layer.edge_width[3] == 3

    new_data = np.random.random((0, 2))
    layer.data = new_data
    assert len(layer.edge_width) == len(new_data)

    new_data = np.random.random((30, 2))
    layer.data = new_data
    assert len(layer.edge_width) == len(new_data)

    # check with `edge_width_is_relative=True`
    data = np.random.random((10, 2))
    layer = Scatter(data)
    layer.edge_width = 0.5
    assert np.all(layer.edge_width == 0.5)

    # raised because `edge_width_is_relative=True` which expects values between 0 and 1
    with pytest.raises(ValueError):
        layer.edge_width = 3

    layer.edge_width_is_relative = False
    layer.edge_width = 3
    assert np.all(layer.edge_width == 3)

    with pytest.raises(ValueError):
        layer.edge_width_is_relative = True


def test_scatter_size():
    data = np.random.random((10, 2))
    layer = Scatter(data)
    layer.size = 3
    assert np.all(layer.size == 3)
    layer.size = np.arange(len(data))
    assert layer.size[0] == 0
    assert layer.size[3] == 3

    new_data = np.random.random((0, 2))
    layer.data = new_data
    assert len(layer.size) == len(new_data)

    new_data = np.random.random((30, 2))
    layer.data = new_data
    assert len(layer.size) == len(new_data)


def test_scatter_color():
    data = np.random.random((10, 2))
    layer = Scatter(data, face_color="white", edge_color="red")
    assert len(layer.face_color) == len(data)
    assert len(layer.edge_color) == len(data)
    np.testing.assert_array_equal(layer.face_color[0], np.asarray([1.0, 1.0, 1.0, 1.0]))
    np.testing.assert_array_equal(layer.edge_color[5], np.asarray([1.0, 0.0, 0.0, 1.0]))

    layer.edge_color = np.asarray([1.0, 1.0, 1.0, 1.0])
    np.testing.assert_array_equal(layer.edge_color[0], np.asarray([1.0, 1.0, 1.0, 1.0]))
    layer.face_color = np.asarray([1.0, 0.0, 0.0, 1.0])
    np.testing.assert_array_equal(layer.face_color[4], np.asarray([1.0, 0.0, 0.0, 1.0]))

    # add new dataset with FEWER items
    data = np.random.random((0, 2))
    layer.data = data
    assert len(layer.face_color) == len(data)
    assert len(layer.edge_color) == len(data)

    # add new dataset with MORE items
    data = np.random.random((12, 2))
    layer.data = data
    assert len(layer.face_color) == len(data)
    assert len(layer.edge_color) == len(data)

    # set new colors
    layer.face_color = np.random.random((12, 4))
    assert len(layer.face_color) == len(data)
    assert layer.face_color.shape == (12, 4)
    layer.edge_color = "yellow"
    assert len(layer.edge_color) == len(data)
