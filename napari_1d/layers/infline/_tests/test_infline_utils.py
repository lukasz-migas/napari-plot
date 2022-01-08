"""Test utilities"""
import numpy as np
import pytest

from napari_1d.layers.infline._infline_constants import Orientation
from napari_1d.layers.infline._infline_utils import parse_infline_orientation


def test_none():
    data, orientations = parse_infline_orientation(None)
    assert len(data) == len(orientations)


@pytest.mark.parametrize("orientation", ("vertical", Orientation.VERTICAL))
def test_tuple_single(orientation):
    data, orientations = parse_infline_orientation((50, orientation))
    assert len(data) == len(orientations)


@pytest.mark.parametrize("orientation", ("vertical", Orientation.VERTICAL))
def test_list_of_tuples(orientation):
    inputs = [(50, orientation), (100, orientation)]
    data, orientations = parse_infline_orientation(inputs)
    assert len(data) == len(orientations)


@pytest.mark.parametrize("orientation", ("vertical", Orientation.VERTICAL))
def test_array_same_orientation(orientation):
    data, orientations = parse_infline_orientation(np.arange(10), orientation)
    assert len(data) == len(orientations)
