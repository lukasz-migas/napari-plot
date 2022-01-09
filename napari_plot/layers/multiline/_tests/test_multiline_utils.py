"""Test utilities."""
import numpy as np
import pytest

from napari_plot.layers.multiline._multiline_utils import (
    check_keys,
    check_length,
    get_data_limits,
    make_multiline_color,
    make_multiline_connect,
    make_multiline_line,
)


def make_data():
    """Make data for tests below."""
    xs = [np.array([0, 0.5, 1]), np.array([0, 1, 2, 50])]
    ys = [np.array([-100, 1, 2]), np.array([0, 1, 2, 3])]
    color = np.full((2, 4), [1.0, 0.0, 0.0, 1.0])
    return xs, ys, color


def test_get_data_limits():
    xs, ys, _ = make_data()

    limits = get_data_limits(xs, ys)
    ylimits = limits[:, 0]
    assert min(ylimits) == -100
    assert max(ylimits) == 3
    xlimits = limits[:, 1]
    assert min(xlimits) == 0
    assert max(xlimits) == 50


def test_check_keys():
    assert check_keys({"A": None, "B": None}, ("A", "B"))
    assert not check_keys({"A": None, "B": None}, ("A", "B", "C"))


def test_check_length():
    check_length(np.arange(10), np.arange(10))
    with pytest.raises(ValueError):
        check_length(np.arange(10), np.arange(12))
    with pytest.raises(ValueError):
        check_length(np.arange(10), np.random.random((10, 2)))


def test_make_multiline_color():
    _, ys, color = make_data()

    colors = make_multiline_color(ys, color)
    assert isinstance(colors, np.ndarray)
    assert colors.shape == (7, 4)  # color for each element
    assert colors.max() <= 1.0


def test_make_multiline_connect():
    _, ys, _ = make_data()

    connect = make_multiline_connect(ys)
    assert isinstance(connect, np.ndarray)
    assert connect.shape == (5, 2)  # excludes edges


def test_make_multiline_line():
    xs, ys, color = make_data()

    pos, connect, colors = make_multiline_line(xs, ys, color)

    # make sure pos is correct
    assert isinstance(pos, np.ndarray)
    assert pos.shape == (7, 2)  # each element

    # make sure colors are correct
    assert isinstance(colors, np.ndarray)
    assert colors.shape == (7, 4)  # color for each element
    assert colors.max() <= 1.0

    # make sure connect is correct
    assert isinstance(connect, np.ndarray)
    assert connect.shape == (5, 2)  # excludes edges
