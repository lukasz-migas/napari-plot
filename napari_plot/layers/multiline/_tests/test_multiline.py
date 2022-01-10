"""Test MultiLine."""
import numpy as np
import pytest

from napari_plot.layers.multiline import MultiLine


def test_multiline_empty():
    layer = MultiLine(None)
    assert layer.ndim == 2


def test_multiline_default():
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
        {"x": np.random.random(10), "ys": [np.random.random(10)]},
        (np.random.random(10), np.random.random(10)),
        ([np.random.random(10)], [np.random.random(10)]),
    ),
)
def test_multiline_inputs_single(data):
    layer = MultiLine(data)
    assert layer._data_view.n_lines == 1


@pytest.mark.parametrize(
    "data",
    (
        {"xs": [np.random.random(10)], "ys": [np.random.random(10)] * 3},
        {"xs": [np.random.random(10)] * 3, "ys": [np.random.random(10)] * 3},
        {"x": np.random.random(10), "ys": [np.random.random(10)] * 3},
    ),
)
def test_multiline_inputs_multiple(data):
    layer = MultiLine(data)
    assert layer._data_view.n_lines == 3


def test_multiline_color():
    data = {"xs": [np.random.random(10)], "ys": [np.random.random(10)]}
    layer = MultiLine(data, color="white")
    assert layer._data_view.n_lines == 1
    np.testing.assert_array_equal(layer.color[0], np.asarray([1.0, 1.0, 1.0, 1.0]))

    layer = MultiLine(data, color="red")
    assert layer._data_view.n_lines == 1
    np.testing.assert_array_equal(layer.color[0], np.asarray([1.0, 0.0, 0.0, 1.0]))

    data = {"xs": [np.random.random(10)], "ys": [np.random.random(10)] * 2}
    layer = MultiLine(data, color="red")
    assert layer._data_view.n_lines == 2
    np.testing.assert_array_equal(layer.color[0], np.asarray([1.0, 0.0, 0.0, 1.0]))
    np.testing.assert_array_equal(layer.color[1], np.asarray([1.0, 0.0, 0.0, 1.0]))


def test_multiline_color_change():
    data = {"xs": [np.random.random(10)], "ys": [np.random.random(10)] * 3}
    layer = MultiLine(data, color="white")
    assert layer._data_view.n_lines == 3
    np.testing.assert_array_equal(layer.color[0], np.asarray([1.0, 1.0, 1.0, 1.0]))

    layer.color = np.full((3, 4), fill_value=(0.0, 1.0, 0.0, 1.0))
    np.testing.assert_array_equal(layer.color[1], np.asarray([0.0, 1.0, 0.0, 1.0]))
    np.testing.assert_array_equal(layer.color[2], np.asarray([0.0, 1.0, 0.0, 1.0]))

    layer.update_color(1, np.array((1.0, 0.0, 1.0, 1.0)))
    np.testing.assert_array_equal(layer.color[1], np.asarray([1.0, 0.0, 1.0, 1.0]))


def test_multiline_add():
    # add single line
    data = {"xs": [np.random.random(10)], "ys": [np.random.random(10)]}
    layer = MultiLine(data)
    assert layer._data_view.n_lines == 1

    data = {"xs": [np.random.random(10)], "ys": [np.random.random(10)]}
    layer.add(data)
    assert layer._data_view.n_lines == 2

    data = {"xs": [np.random.random(10)] * 3, "ys": [np.random.random(10)] * 3}
    layer.add(data)
    assert layer._data_view.n_lines == 5


def test_multiline_stream():
    data = {"xs": [np.random.random(10)] * 3, "ys": [np.random.random(10)] * 3}
    layer = MultiLine(data)
    assert layer._data_view.n_lines == 3
    new_data = {"xs": [np.random.random(10)] * 3, "ys": [np.random.random(10)] * 3}
    layer.stream(new_data)
    assert layer._data_view.n_lines == 3
