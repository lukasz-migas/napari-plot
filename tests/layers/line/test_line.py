"""Test Line layer."""

import numpy as np
import pytest

from napari_plot.layers.line import Line


def test_line_empty():
    layer = Line(None)
    assert layer.ndim == 2


@pytest.mark.parametrize("data", [[[0, 1, 2], [1, 2, 3]], np.random.random((10, 2))])
def test_line_data(data):
    layer = Line(data)
    assert isinstance(layer.data, np.ndarray)


def test_line_change_data():
    data = np.random.random((10, 2))
    layer = Line(data)

    new_data = np.random.random(10)
    layer.x = new_data
    layer.y = new_data

    data = np.random.random((20, 2))
    layer.data = data
    with pytest.raises(ValueError):
        layer.x = new_data
    with pytest.raises(ValueError):
        layer.y = new_data
