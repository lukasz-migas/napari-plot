"""Test InfLineList"""

import numpy as np
import pytest

from napari_plot.layers.infline._infline import HorizontalLine, VerticalLine
from napari_plot.layers.infline._infline_list import InfiniteLineList


def test_empty_infline_list():
    region_list = InfiniteLineList()
    assert len(region_list.orientations) == 0


def test_adding_to_list():
    np.random.seed(0)
    data = np.random.random(1)
    vert = VerticalLine(data)
    line_list = InfiniteLineList()
    line_list.add(vert)
    assert len(line_list.orientations) == 1
    assert line_list.inflines[0] == vert
    assert line_list.orientations[0] == "vertical"
    assert len(line_list.orientations) == len(line_list.z_indices) == len(line_list.color)

    data = np.random.random(1)
    horz = HorizontalLine(data)
    line_list.add(horz)
    assert len(line_list.orientations) == 2
    assert line_list.inflines[1] == horz
    assert line_list.orientations[1] == "horizontal"


def test_bad_color_array():
    """Test adding shapes to InfiniteLineList."""
    np.random.seed(0)
    data = np.random.random(1)
    vert = VerticalLine(data)
    line_list = InfiniteLineList()
    line_list.add(vert)

    # test setting color with a color array of the wrong shape
    bad_color_array = np.array([[0, 0, 0, 1], [1, 1, 1, 1]])
    with pytest.raises(ValueError):
        line_list.color = bad_color_array
