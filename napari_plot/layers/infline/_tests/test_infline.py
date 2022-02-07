"""Inflines."""
import numpy as np
import pytest

from napari_plot.layers.infline import InfLine


def test_empty_infline():
    layer = InfLine(None)
    assert layer.ndim == 2


def test_default_infline():
    # add multiple regions
    data = [25, 50]
    layer = InfLine(data)
    assert layer.n_inflines == len(data)
    assert np.all([o == "vertical" for o in layer.orientation])

    # add single region
    data = [25]
    layer = InfLine(data)
    assert layer.n_inflines == len(data)
    assert np.all([o == "vertical" for o in layer.orientation])


def test_vertical_infline():
    # add multiple regions
    data = [25, 50]
    layer = InfLine(data, orientation="vertical")
    assert layer.n_inflines == len(data)
    assert np.all([o == "vertical" for o in layer.orientation])

    # add single region
    data = [25]
    layer = InfLine(data, orientation="vertical")
    assert layer.n_inflines == len(data)
    assert np.all([o == "vertical" for o in layer.orientation])


def test_horizontal_infline():
    # add multiple regions
    data = [25, 50]
    layer = InfLine(data, orientation="horizontal")
    assert layer.n_inflines == len(data)
    assert np.all([o == "horizontal" for o in layer.orientation])

    # add single region
    data = [25]
    layer = InfLine(data, orientation="horizontal")
    assert layer.n_inflines == len(data)
    assert np.all([o == "horizontal" for o in layer.orientation])


def test_with_orientation():
    # add multiple regions
    data = [(25, "vertical"), (50, "vertical")]
    layer = InfLine(data)
    assert layer.n_inflines == len(data)
    assert np.all([o == "vertical" for o in layer.orientation])

    data = [(250, "horizontal"), (233, "horizontal")]
    layer = InfLine(data)
    assert layer.n_inflines == len(data)
    assert np.all([o == "horizontal" for o in layer.orientation])


def test_adding_inflines():
    data = [25, 50]
    layer = InfLine(data, orientation="vertical")
    assert layer.n_inflines == len(data)
    assert layer.ndim == 2

    new_data = [75, 123]
    layer.add(new_data, orientation="horizontal")
    assert layer.n_inflines == len(data + new_data)


def test_infline_color_default():
    data = [25, 50]
    layer = InfLine(data, orientation="vertical")
    assert layer.n_inflines == len(data)
    assert layer.ndim == 2
    np.testing.assert_array_equal(layer.color[0], np.asarray([1.0, 1.0, 1.0, 1.0]))


@pytest.mark.parametrize("color", ["red", "#FF0000", (1, 0, 0), (1, 0, 0, 1)])
def test_infline_color_set(color):
    data = [25, 50]
    layer = InfLine(data, orientation="vertical", color=color)
    assert layer.n_inflines == len(data)
    assert layer.ndim == 2
    np.testing.assert_array_equal(layer.color[0], np.asarray([1.0, 0.0, 0.0, 1.0]))


@pytest.mark.parametrize("color", ["red", "#FF0000", (1, 0, 0), (1, 0, 0, 1)])
def test_infline_color_update(color):
    data = np.random.random(20)
    layer = InfLine(data, orientation="vertical", color="white")
    assert layer.n_inflines == 20
    layer.color = color
    np.testing.assert_array_equal(layer.color[0], np.asarray([1.0, 0.0, 0.0, 1.0]))
    np.testing.assert_array_equal(layer.color[5], np.asarray([1.0, 0.0, 0.0, 1.0]))


def test_infline_trim():
    data = np.random.random(20)
    layer = InfLine(data, orientation="vertical")
    assert layer.n_inflines == 20
    data = np.random.random(10)
    layer.data = data
    assert layer.n_inflines == 10


def test_infline_color_current():
    data = np.random.random(20)
    layer = InfLine(data, orientation="vertical")
    np.testing.assert_array_equal(layer.color[0], np.asarray([1.0, 1.0, 1.0, 1.0]))

    layer.selected_data = {0, 1}
    assert layer.selected_data == {0, 1}
    layer.current_color = "red"
    np.testing.assert_array_equal(layer.color[1], np.asarray([1.0, 0.0, 0.0, 1.0]))
    np.testing.assert_array_equal(layer.color[2], np.asarray([1.0, 1.0, 1.0, 1.0]))

    layer.selected_data = {9}
    assert layer.selected_data == {9}
    layer.current_color = "#00FF00"
    np.testing.assert_array_equal(layer.color[5], np.asarray([1.0, 1.0, 1.0, 1.0]))
    np.testing.assert_array_equal(layer.color[9], np.asarray([0.0, 1.0, 0.0, 1.0]))


def test_infline_selection():
    data = np.random.random(20)
    layer = InfLine(data, orientation="vertical")
    layer.selected_data = {0, 1}
    assert layer.selected_data == {0, 1}

    layer.selected_data = {9}
    assert layer.selected_data == {9}

    layer.selected_data = set()
    assert layer.selected_data == set()
