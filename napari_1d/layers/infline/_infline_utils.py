"""Infinite line utilities."""
import typing as ty


def extract_inf_line_orientation(data, orientation=None):
    """Separate orientation from data if present and return both."""
    # Tuple for one shape or list of lines with orientation
    if isinstance(data, ty.Tuple):
        data, orientation = data
    # List of (position, orientation) tuples
    elif len(data) != 0 and all(isinstance(dat, ty.Tuple) for dat in data):
        orientation = [dat[1] for dat in data]
        data = [dat[0] for dat in data]
    return data, orientation


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
