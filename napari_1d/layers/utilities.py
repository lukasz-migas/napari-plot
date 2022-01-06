import typing as ty

import numpy as np

from napari_1d.layers.infline._infline_constants import Orientation


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
    min_val, max_val = np.iinfo(np.int64).min, np.iinfo(np.int64).max
    i = 0
    for (val, orientation, color) in zip(data, orientations, colors):
        if orientation == Orientation.VERTICAL:
            _pos = [[val, min_val], [val, max_val]]
        else:
            _pos = [[min_val, val], [max_val, val]]

        _colors.extend([color, color])
        pos.extend(_pos)
        connect.append([i, i + 1])
        i += 2
    return np.asarray(pos, dtype=object), np.asarray(connect, dtype=object), np.asarray(_colors, dtype=object)


def make_infinite_pos(data: np.ndarray, orientations: ty.Iterable[Orientation]):
    """Create position in format x,y"""
    pos = []
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
