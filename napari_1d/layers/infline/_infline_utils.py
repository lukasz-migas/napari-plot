"""Infinite line utilities."""
import typing as ty

import numpy as np

from ._infline_constants import Orientation


def parse_inf_line_orientation(data, orientation=None):
    """Separate orientation from data if present and return both."""
    # Data is None so return empty array
    if data is None:
        data, orientation = [], []
    # Tuple for one shape or list of lines with orientation
    elif isinstance(data, ty.Tuple):
        data, orientation = data
        data = [data]
        orientation = [orientation]
    # List of (position, orientation) tuples
    elif len(data) != 0 and all(isinstance(dat, ty.Tuple) for dat in data):
        orientation = [dat[1] for dat in data]
        data = [dat[0] for dat in data]
    # Iterable of position without orientation
    elif isinstance(data, ty.Iterable) and isinstance(orientation, (str, Orientation)):
        orientation = [orientation] * len(data)

    return np.asarray(data), orientation


def get_default_infline_type(current_type):
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


def nearby_line(distance, max_dist: float):
    """Returns mask of nearest elements and if they meet the distance criteria."""
    return np.where(np.any(np.abs(distance) < max_dist, axis=1))[0]


def lines_intersect_box(lines, corners):
    """Return indices of lines that intersect with the box."""
    y, x = corners[:, 0], corners[:, 1]
    ymin, ymax = np.min(y), np.max(y)
    xmin, xmax = np.min(x), np.max(x)

    # check whether any x-axis elements are between the x-min, x-max
    x_mask = np.logical_and(lines[:, 0] > xmin, lines[:, 0] < xmax)
    y_mask = np.logical_and(lines[:, 1] > ymin, lines[:, 1] < ymax)
    return np.where(np.logical_or(x_mask, y_mask))[0]
