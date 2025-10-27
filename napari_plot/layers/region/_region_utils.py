"""Region utils."""

from __future__ import annotations

import typing as ty
import warnings

import numpy as np

from napari_plot.layers.region._region_constants import Orientation


def check_data(data):
    """Check whether data is iterable of two elements."""
    if not isinstance(data, ty.Iterable) or len(data) != 2:
        raise ValueError("Expected two-element iterable.")


def parse_infinite_region_orientation(data, orientation=None) -> tuple[list, list]:
    """Separate orientation from data if present and return both."""
    # Data is None so return empty lists
    if data is None:
        return [], []
    # Tuple for one shape or list of shapes with shape_type
    if isinstance(data, tuple):
        data, orientation = data
        data, orientation = [data], [orientation]
    # List of (windows, shape_type) or (window min, window max) tuples
    elif len(data) != 0 and all(isinstance(dat, tuple) for dat in data):
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
    # check size and shape of each element
    for dat in data:
        check_data(dat)
    return data, orientation


def preprocess_box(data):
    """Pre-process data to take correct values."""
    return [[data[2], data[0]], [data[3], data[1]]]


def make_infinite_region_simple_data(
    data: np.ndarray,
    orientations: ty.Iterable[Orientation],
    colors: np.ndarray,
    indices: ty.Optional[ty.List[int]] = None,
):
    """Create all elements required to create infinite region.

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
    assert len(data) == len(orientations) == len(colors), (
        "The number of points must match the number of orientations and colors."
    )
    if indices is None:
        indices = np.arange(len(data))
    if len(indices) == 0:
        return np.zeros(0), np.zeros(0), np.zeros((0, 4))

    i = 0
    pos_ = np.zeros((len(indices), 2), dtype=np.float32)
    orientation_ = np.zeros(len(indices), dtype=np.float32)
    colors_ = np.zeros((len(indices), 4), dtype=np.float32)
    for index, ((min_val, max_val), orientation, color) in enumerate(zip(data, orientations, colors)):
        if index in indices:
            pos_[i] = (min_val, max_val)
            orientation_[i] = 0 if orientation == Orientation.VERTICAL else 1
            colors_[i] = color
            i += 1

    if len(pos_) == 0:
        return np.zeros(0), np.zeros(0), np.zeros((0, 4))
    return (
        np.asarray(pos_, dtype=np.float32),
        np.asarray(orientation_, dtype=np.float32),
        np.asarray(colors_, dtype=np.float32),
    )


def make_infinite_region_pos(
    data: np.ndarray,
    orientations: ty.Iterable[Orientation],
    indices: ty.Optional[ty.List[int]] = None,
):
    """Create position in format x,y"""
    pos = []
    if len(data) == 0:
        return np.zeros((0, 2))
    if indices is None:
        indices = np.arange(len(data))

    for index, ((min_val, max_val), orientation) in enumerate(zip(data, orientations)):
        if index in indices:
            pos_ = (
                [[min_val, np.nan], [max_val, np.nan]]
                if orientation == Orientation.VERTICAL
                else [[np.nan, min_val], [np.nan, max_val]]
            )
            pos.extend(pos_)
    return np.asarray(pos, dtype=np.float32)


def make_infinite_region_mean(
    data: np.ndarray,
    orientations: ty.Iterable[Orientation],
    indices: ty.Optional[ty.List[int]] = None,
):
    """Create position in format x,y"""
    pos = []
    if len(data) == 0:
        return np.zeros((0, 2))
    if indices is None:
        indices = np.arange(len(data))

    for index, ((min_val, max_val), orientation) in enumerate(zip(data, orientations)):
        if index in indices:
            pos.append(
                [np.mean([min_val, max_val]), np.nan]
                if orientation == Orientation.VERTICAL
                else [np.nan, np.mean([min_val, max_val])]
            )
    return np.asarray(pos, dtype=np.float32)


def make_infinite_region_color(colors) -> np.ndarray:
    """Create properly formatted colors."""
    _colors = []
    for color in colors:
        _colors.extend([color, color])
    return np.asarray(_colors, dtype=object)


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


def nearby_line(distance, max_dist: float):
    """Returns mask of nearest elements and if they meet the distance criteria."""
    return np.where(np.any(np.abs(distance) < max_dist, axis=1))[0]


def region_intersect_box(lines, corners):
    """Return indices of lines that intersect with the box."""
    y, x = corners[:, 0], corners[:, 1]
    ymin, ymax = np.min(y), np.max(y)
    xmin, xmax = np.min(x), np.max(x)

    # check whether any x-axis elements are between the x-min, x-max
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        x_mask = np.logical_and(lines[:, 0] > xmin, lines[:, 0] < xmax)
        y_mask = np.logical_and(lines[:, 1] > ymin, lines[:, 1] < ymax)
        indices = np.where(np.logical_or(x_mask, y_mask))[0]
        return indices
