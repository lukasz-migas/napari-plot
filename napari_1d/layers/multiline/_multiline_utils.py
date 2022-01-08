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


def parse_multiline_data(data) -> ty.Tuple[ty.List[np.ndarray], ty.List[np.ndarray]]:
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
        elif check_keys(data, ("x", "ys")) and all(
            [isinstance(data["x"], np.ndarray), isinstance(data["ys"], ty.List)]
        ):
            xs = [data["x"]]
            ys = data["ys"]
        # Dict with `ys` list of arrays
        elif check_keys(data, ("ys",) and isinstance(data["ys"], ty.List)):
            ys = data["ys"]
    else:
        raise NotImplementedError("Could not parse provided data.")

    if len(xs) == 1:
        for y in ys:
            check_length(xs[0], y)
    else:
        for x, y in zip(xs, ys):
            check_length(x, y)
    return xs, ys
