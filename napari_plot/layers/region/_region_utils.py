"""Region utils."""
import typing as ty

import numpy as np


def extract_region_orientation(data, orientation=None):
    """Separate orientation from data if present and return both."""
    # Tuple for one shape or list of shapes with shape_type
    if isinstance(data, ty.Tuple):
        data, orientation = data
    # List of (windows, shape_type) tuples
    elif len(data) != 0 and all(isinstance(dat, ty.Tuple) for dat in data):
        orientation = [dat[1] for dat in data]
        data = [dat[0] for dat in data]
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
