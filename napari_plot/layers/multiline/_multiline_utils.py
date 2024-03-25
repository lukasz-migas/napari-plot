"""Utilities."""

import typing as ty

import numpy as np


def check_length(x: np.ndarray, y: np.ndarray):
    """Check length of two arrays."""
    if x.ndim > 1 or y.ndim > 1:
        raise ValueError("Make sure to provide 1D arrays.")
    if x.size != y.size:
        raise ValueError("Make sure to provide two arrays of equal size and shape.")


def check_keys(data: ty.Dict, keys: ty.Tuple):
    """Check whether keys exist in particular dictionary."""
    return all([key in data for key in keys])


def parse_multiline_data(data, check: bool = True) -> ty.Tuple[ty.List[np.ndarray], ty.List[np.ndarray]]:
    """Parse data to be displayed in multiline layer."""
    xs, ys = [], []
    # Data can be None in which case return two empty lists.
    if data is None:
        return xs, ys
    # Data is a tuple of two arrays
    elif isinstance(data, ty.Tuple):
        x, y = data
        if all([isinstance(dat, np.ndarray) for dat in (x, y)]):
            xs, ys = [x], [y]
        elif all([isinstance(dat, ty.List) for dat in (x, y)]):
            xs, ys = x, y
    # Data is a dict with `xs` and `ys` keys
    elif isinstance(data, ty.Dict):
        # Dict with `xs` and `ys` lists of arrays
        if check_keys(data, ("xs", "ys")) and all([isinstance(dat, ty.List) for dat in (data["xs"], data["ys"])]):
            xs, ys = data["xs"], data["ys"]
            if len(xs) > len(ys):
                raise ValueError(
                    "When providing `xs` and `ys` arrays, the `xs` array must have 1 array or as many arrays as the"
                    " `ys` arrays."
                )
        # Dict with `x` array and `ys` list of arrays
        elif check_keys(data, ("x", "ys")):
            if all([isinstance(data["x"], np.ndarray), isinstance(data["ys"], ty.List)]):
                xs = [data["x"]]
                ys = data["ys"]
            elif all([isinstance(data["x"], np.ndarray), isinstance(data["ys"], np.ndarray)]):
                xs = [data["x"]]
                ys = np.atleast_2d(data["ys"])
                if ys.shape[1] != xs[0].size:
                    ys = ys.T
        # Dict with `ys` list of arrays
        elif check_keys(data, ("ys",)) and isinstance(data["ys"], ty.List):
            ys = data["ys"]
    else:
        raise NotImplementedError("Could not parse provided data.")

    if check:
        if len(xs) == 1:
            for y in ys:
                check_length(xs[0], y)
        else:
            for x, y in zip(xs, ys):
                check_length(x, y)
    return xs, ys


def make_multiline_line(xs: ty.List, ys: ty.List, colors: np.ndarray):
    """Create all elements required to create multiline lines."""
    pos, connect, _colors = [], [], []
    if len(xs) == 1:
        xs = [xs[0]] * len(ys)

    start = 0
    for x, y, color in zip(xs, ys, colors):
        n = len(x)
        # data
        pos.append(np.c_[x, y])

        # connect
        _connect = np.empty((n - 1, 2), np.float32)
        _connect[:, 0] = np.arange(start=start, stop=start + n - 1)
        _connect[:, 1] = _connect[:, 0] + 1
        connect.append(_connect)
        start = _connect[-1, 1] + 1

        # add color
        _colors.append(np.full((n, 4), fill_value=color, dtype=np.float32))
    pos = np.vstack(pos)
    colors = np.vstack(_colors)
    connect = np.vstack(connect)
    return pos, connect, colors


def make_multiline_pos(xs: ty.List, ys: ty.List):
    """Create array of how points should be connected."""
    pos = []

    if len(xs) == 1:
        xs = [xs[0]] * len(ys)
    for x, y in zip(xs, ys):
        # data
        pos.append(np.c_[x, y])
    return np.vstack(pos)


def make_multiline_connect(ys: ty.List):
    """Create array of how points should be connected."""
    connect = []
    start = 0
    for y in ys:
        n = len(y)

        _connect = np.empty((n - 1, 2), np.float32)
        _connect[:, 0] = np.arange(start=start, stop=start + n - 1)
        _connect[:, 1] = _connect[:, 0] + 1
        connect.append(_connect)
        start = _connect[-1, 1] + 1
    return np.vstack(connect)


def make_multiline_color(ys: ty.List, colors: np.ndarray):
    """Create all elements required to create multiline lines."""
    _colors = []
    for y, color in zip(ys, colors):
        _colors.append(np.full((len(y), 4), fill_value=color, dtype=np.float32))
    colors = np.vstack(_colors)
    return colors


def get_data_limits(xs: ty.List, ys: ty.List) -> np.ndarray:
    """Get data limits along both axes."""
    x = [(np.min(v), np.max(v)) for v in xs]
    y = [(np.min(v), np.max(v)) for v in ys]
    return np.asarray([[np.min(y), np.min(x)], [np.max(y), np.max(x)]])
