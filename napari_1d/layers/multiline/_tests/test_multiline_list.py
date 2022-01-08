"""Test MultiLineList"""
import numpy as np
import pytest

from napari_1d.layers.multiline._multiline_list import MultiLineList


def test_empty_infline_list():
    line_list = MultiLineList()
    assert line_list.n_lines == 0


def test_adding_to_list():
    np.random.seed(0)

    # add single line
    xs = [np.random.random(10)]
    ys = [np.random.random(10)]
    color = np.random.random((1, 4))
    line_list = MultiLineList()
    line_list.add(xs, ys, color)
    assert len(line_list.xs) == len(line_list.ys)
    assert line_list.xs_equal_ys
    assert len(line_list.color) == 1

    # add five more lines
    xs = []
    ys = [np.random.random(10)] * 5
    color = np.random.random((5, 4))
    line_list.add(xs, ys, color)
    assert len(line_list.xs) == 1
    assert len(line_list.ys) == 6
    assert len(line_list.color) == 6
    assert len(line_list.xs) != len(line_list.ys)
    assert not line_list.xs_equal_ys

    xs = [np.random.random(10)] * 5
    ys = [np.random.random(10)] * 5
    color = np.random.random((5, 4))
    with pytest.raises(ValueError):
        line_list.add(xs, ys, color)
