"""Various utilities"""

import typing as ty

import numpy as np


def find_nearest_index(data: np.ndarray, value: ty.Union[float, np.ndarray, ty.Iterable]):
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
    if data.size == 0:
        return
    if isinstance(value, ty.Iterable):
        return [np.argmin(np.abs(data - _value)) for _value in value]
    return np.argmin(np.abs(data - value))


def get_min_max(values):
    """Get the minimum and maximum value of an array"""
    if values is None or len(values) == 0:
        return [None, None]
    return [np.min(values), np.max(values)]
