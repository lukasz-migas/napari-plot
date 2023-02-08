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
