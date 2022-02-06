"""Region utils."""
import typing as ty

import numpy as np

from ._region_constants import Orientation


def check_data(data):
    """Check whether data is iterable of two elements."""
    if not isinstance(data, ty.Iterable) or len(data) != 2:
        raise ValueError("Expected two-element iterable.")


def parse_region_data(data, orientation=None) -> ty.Tuple[ty.List, ty.List]:
    """Separate orientation from data if present and return both."""
    # Data is None so return empty lists
    if data is None:
        return [], []
    # Tuple for one shape or list of shapes with shape_type
    elif isinstance(data, ty.Tuple):
        data, orientation = data
        data, orientation = [data], [orientation]
    # List of (windows, shape_type) or (window min, window max) tuples
    elif len(data) != 0 and all(isinstance(dat, ty.Tuple) for dat in data):
        _data, _orientation = [], []
        for el1, el2 in data:
            if not isinstance(el2, (str, Orientation)):
                _data.append((el1, el2))
                _orientation.append(orientation)
            else:
                _data.append(el1)
                _orientation.append(el2)
        orientation = _orientation
        data = _data
    # Iterable of data without orientation
    elif isinstance(data, ty.Iterable) and isinstance(orientation, (str, Orientation)):
        orientation = [orientation] * len(data)
    for dat in data:
        check_data(dat)
    return data, orientation


def preprocess_region(data, orientation):
    """Pre-process data to proper format."""
    min_val, max_val = np.iinfo(np.int64).min, np.iinfo(np.int64).max
    start, end = data
    if orientation == "vertical":
        region = [[min_val, start], [min_val, end], [max_val, end], [max_val, start]]
    else:
        region = [[start, min_val], [start, max_val], [end, max_val], [end, min_val]]
    return region


def preprocess_box(data):
    """Pre-process data to take correct values."""
    return [[data[2], data[0]], [data[3], data[1]]]


def get_default_region_type(current_type):
    """If all shapes in current_type are of identical shape type,
       return this shape type, else "polygon" as lowest common
       denominator type.

    Parameters
    ----------
    current_type : list of str
        list of current shape types

    Returns
    ----------
    default_type : str
        default shape type
    """
    default = "vertical"
    if not current_type:
        return default
    first_type = current_type[0]
    if all(shape_type == first_type for shape_type in current_type):
        return first_type
    return default
