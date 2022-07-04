"""Various utilities"""
import typing as ty
from contextlib import suppress

import numpy as np


def find_nearest_index(data: np.ndarray, value: ty.Union[int, float, np.ndarray, ty.Iterable]):
    """Find nearest index of asked value

    Parameters
    ----------
    data : np.array
        input array (e.g. m/z values)
    value : Union[int, float, np.ndarray]
        asked value

    Returns
    -------
    index :
        index value
    """
    data = np.asarray(data)
    if isinstance(value, ty.Iterable):
        return [np.argmin(np.abs(data - _value)) for _value in value]
    return np.argmin(np.abs(data - value))


def get_min_max(values):
    """Get the minimum and maximum value of an array"""
    return [np.min(values), np.max(values)]


def connect(connectable, func: ty.Callable, state: bool = True):
    """Function that connects/disconnects."""
    with suppress(Exception):
        connectable = getattr(connectable, "connect") if state else getattr(connectable, "disconnect")
        connectable(func)


class Cycler:
    """Cycling class similar to itertools.cycle with the addition of `previous` functionality"""

    def __init__(self, c):
        self._c = c
        self._index = -1

    def __len__(self):
        return len(self._c)

    def __next__(self):
        self._index += 1
        if self._index >= len(self._c):
            self._index = 0
        return self._c[self._index]

    def __call__(self):
        return self.next()

    @property
    def index(self) -> int:
        """Return current index."""
        return self._index

    @property
    def count(self) -> int:
        """Return the total number of elements in the cycler."""
        return len(self._c)

    def next(self):
        """Go forward"""
        return self.__next__()

    def previous(self):
        """Go backwards"""
        self._index -= 1
        if self._index < 0:
            self._index = len(self._c) - 1
        return self._c[self._index]

    def current(self):
        """Get current index"""
        return self._c[self._index]

    def set_current(self, index: int):
        """Set current index."""
        self._index = index
