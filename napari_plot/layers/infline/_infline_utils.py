"""Infinite line utilities."""

import typing as ty

import numpy as np

from napari_plot.layers.infline._infline_constants import Orientation


def make_infinite_line(
    data: np.ndarray,
    orientations: ty.Iterable[Orientation],
    colors: np.ndarray,
    indices: ty.Optional[ty.List[int]] = None,
):
    """Create all elements required to create infinite lines.

    Parameters
    ----------
    data : np.ndarray
        Array containing positions of each infinite line.
    orientations : ty.Iterable[Orientation]
        Iterable containing orientation of each line. Values are ordered in different manner depending on whether it is
        a horizontal or vertical line.
    colors : np.ndarray
        Array containing color of each line.
    indices : ty.List[int], optional
        List containing indices of lines to be included in the final display.
    """
    assert (
        len(data) == len(orientations) == len(colors)
    ), "The number of points must match the number of orientations and colors."

    if indices is None:
        indices = np.arange(len(data))

    pos, connect, _colors = [], [], []
    if len(indices) == 0:
        return np.zeros((0, 2)), np.zeros((0, 2)), np.zeros((0, 4))

    min_val, max_val = np.iinfo(np.int64).min * 15, np.iinfo(np.int64).max * 15
    i = 0
    for index, (val, orientation, color) in enumerate(zip(data, orientations, colors)):
        if index in indices:
            if orientation == Orientation.VERTICAL:
                _pos = [[val, min_val], [val, max_val]]
            else:
                _pos = [[min_val, val], [max_val, val]]

            _colors.extend([color, color])
            pos.extend(_pos)
            connect.append([i, i + 1])
            i += 2
    if len(pos) == 0:
        return np.zeros((0, 2)), np.zeros((0, 2)), np.zeros((0, 4))
    return (
        np.asarray(pos, dtype=np.float32),
        np.asarray(connect, dtype=np.float32),
        np.asarray(_colors, dtype=np.float32),
    )


def make_infinite_pos(data: np.ndarray, orientations: ty.Iterable[Orientation]):
    """Create position in format x,y"""
    pos = []
    if len(data) == 0:
        return np.zeros((0, 2))
    for val, orientation in zip(data, orientations):
        if orientation == Orientation.VERTICAL:
            _pos = [val, np.nan]
        else:
            _pos = [np.nan, val]
        pos.extend([_pos])

    return np.asarray(pos, dtype=np.float32)


def make_infinite_color(colors) -> np.ndarray:
    """Create properly formatted colors."""
    _colors = []
    for color in colors:
        _colors.extend([color, color])
    return np.asarray(_colors, dtype=object)


def parse_infline_orientation(data, orientation=None):
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
