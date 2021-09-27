"""Infinite line utilities."""
import typing as ty

import numpy as np


def extract_inf_line_orientation(data, orientation=None):
    """Separate orientation from data if present and return both."""
    if isinstance(data, ty.Tuple):
        data, orientation = data
    return data, orientation


def inside(coordinates, data: np.ndarray, max_dist: float = 1.0):
    """Check whether there are any lines nearby."""
    return set()
