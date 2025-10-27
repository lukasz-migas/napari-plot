"""Region based on Rectangle."""

from enum import Enum

from napari.layers.shapes._shapes_models.rectangle import Rectangle


class Orientation(str, Enum):
    """Orientation"""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


def preprocess_box(data):
    """Pre-process data to take correct values."""
    return [[data[2], data[0]], [data[3], data[1]]]


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
