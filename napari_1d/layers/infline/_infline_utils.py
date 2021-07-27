"""Infinite line utilities."""
import typing as ty


def extract_inf_line_orientation(data, orientation=None):
    """Separate orientation from data if present and return both."""
    if isinstance(data, ty.Tuple):
        data, orientation = data
    return data, orientation
