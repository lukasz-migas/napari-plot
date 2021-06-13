"""Various utilities"""
import numpy as np
from typing import Iterable, Union


def find_nearest_index(
    data: np.ndarray, value: Union[int, float, np.ndarray, Iterable]
):
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
    if isinstance(value, Iterable):
        return [np.argmin(np.abs(data - _value)) for _value in value]
    return np.argmin(np.abs(data - value))


def get_min_max(values):
    """Get the minimum and maximum value of an array"""
    return [np.min(values), np.max(values)]
