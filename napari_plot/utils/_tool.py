"""Region based on Rectangle."""

import typing as ty
from enum import Enum

import numpy as np
from napari.layers.shapes._shapes_models.rectangle import Rectangle


class Orientation(str, Enum):
    """Orientation"""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


def preprocess_box(data):
    """Pre-process data to take correct values."""
    return [[data[2], data[0]], [data[3], data[1]]]


def preprocess_region(data, orientation) -> ty.List:
    """Pre-process data to proper format."""
    start, end = np.asarray(data, dtype=np.float32)
    min_val = np.finfo(np.float32).min / 1e30
    max_val = np.finfo(np.float32).max / 1e30
    if orientation == "vertical":
        return [[min_val, start], [min_val, end], [max_val, end], [max_val, start]]
    return [[start, min_val], [start, max_val], [end, max_val], [end, min_val]]


class Vertical(Rectangle):
    """Class for vertical region"""

    def __init__(
        self,
        data,
        *,
        z_index=0,
        dims_order=None,
        ndisplay=2,
    ):
        if len(data) == 2:
            data = preprocess_region(data, "vertical")

        super().__init__(
            data,
            edge_width=1,
            z_index=z_index,
            dims_order=dims_order,
            ndisplay=ndisplay,
        )
        self.name = "vertical"


class Horizontal(Rectangle):
    """Class for horizontal region"""

    def __init__(
        self,
        data,
        *,
        z_index=0,
        dims_order=None,
        ndisplay=2,
    ):
        if len(data) == 2:
            data = preprocess_region(data, "horizontal")

        super().__init__(
            data,
            edge_width=1,
            z_index=z_index,
            dims_order=dims_order,
            ndisplay=ndisplay,
        )
        self.name = "horizontal"


class Box(Rectangle):
    """Class for rectangular box region."""

    def __init__(
        self,
        data,
        *,
        edge_width=1,
        z_index=0,
        dims_order=None,
        ndisplay=2,
    ):
        if len(data) != 4:
            raise ValueError("Please provide 4 values in order: x_min, x_max, y_min, y_max.")
        data = preprocess_box(data)
        super().__init__(
            data,
            edge_width=edge_width,
            z_index=z_index,
            dims_order=dims_order,
            ndisplay=ndisplay,
        )
        self.name = "box"


region_classes = {Orientation.HORIZONTAL: Horizontal, Orientation.VERTICAL: Vertical}
