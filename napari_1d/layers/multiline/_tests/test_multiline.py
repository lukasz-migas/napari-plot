"""Test MultiLine."""
import numpy as np
import pytest

from napari_1d.layers.multiline import MultiLine


def test_empty_multiline():
    layer = MultiLine(None)
    assert layer.ndim == 2


def test_default_multiline():
    # add no data
    data = None
    layer = MultiLine(data)
    assert layer._data_view.n_lines == 0

    # add single line
    data = {"xs": [np.random.random(10)], "ys": [np.random.random(10)]}
    layer = MultiLine(data)
    assert layer._data_view.n_lines == 1


@pytest.mark.parametrize(
    "data",
    (
        {"xs": [np.random.random(10)], "ys": [np.random.random(10)]},
        {"xs": [np.random.random(10)], "ys": [np.random.random(10)] * 3},
        {"x": np.random.random(10), "ys": [np.random.random(10)]},
        {"x": np.random.random(10), "ys": [np.random.random(10)] * 3},
    ),
)
def test_multiline_inputs(data):
    layer = MultiLine(data)
    assert layer._data_view.n_lines > 0
