import numpy as np
import pytest

from napari_plot.layers.region._region import Horizontal, Vertical
from napari_plot.layers.region._region_list import RegionList


def test_empty_region_list():
    region_list = RegionList()
    assert len(region_list.orientations) == 0


def test_adding_to_list():
    np.random.seed(0)
    data = np.random.random((2,))
    vert = Vertical(data)
    region_list = RegionList()
    region_list.add(vert)
    assert len(region_list.orientations) == 1
    assert region_list.regions[0] == vert
    assert region_list.orientations[0] == "vertical"

    horz = Horizontal(data)
    region_list.add(horz)
    assert len(region_list.orientations) == 2
    assert region_list.regions[1] == horz
    assert region_list.orientations[1] == "horizontal"


def test_bad_color_array():
    """Test adding shapes to ShapeList."""
    np.random.seed(0)
    data = np.random.random((2,))
    vert = Vertical(data)
    region_list = RegionList()
    region_list.add(vert)

    # test setting color with a color array of the wrong shape
    bad_color_array = np.array([[0, 0, 0, 1], [1, 1, 1, 1]])
    with pytest.raises(ValueError):
        region_list.color = bad_color_array
