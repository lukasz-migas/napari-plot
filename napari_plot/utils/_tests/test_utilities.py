"""Test utilities."""
import numpy as np
from napari.utils.events import EventedList

from napari_plot.utils.utilities import connect, find_nearest_index, get_min_max


def test_find_nearest_index():
    """Test find the nearest index."""
    data = np.array([1, 2, 3, 4, 5])
    assert find_nearest_index(data, 3) == 2
    np.testing.assert_array_equal(find_nearest_index(data, [1, 3, 5]), [0, 2, 4])


def test_get_min_max():
    """Test get the minimum and maximum value of an array."""
    data = np.array([1, 2, 3, 4, 5])
    np.testing.assert_array_equal(get_min_max(data), [1, 5])


def test_connect():
    """Test connect/disconnect."""
    # this does nothing because 'None' does not have a 'connect' method
    connect(None, print, state=True)
    connect(None, print, state=False)

    def func():
        nonlocal count
        count += 1

    count = 0
    obj = EventedList()
    obj.insert(0, "TEST")
    assert count == 0
    connect(obj.events.inserting, func, state=True)
    obj.insert(0, "TEST")
    assert count == 1
    connect(obj.events.inserting, func, state=False)
    obj.insert(0, "TEST")
    assert count == 1
