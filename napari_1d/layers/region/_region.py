"""Region based on Rectangle."""
from napari.layers.shapes._shapes_models.rectangle import Rectangle
from ._region_utils import preprocess_region


class Vertical(Rectangle):
    """Class for vertical region"""

    def __init__(
        self,
        data,
        *,
        edge_width=1,
        z_index=0,
        dims_order=None,
        ndisplay=2,
    ):
        if len(data) == 2:
            data = preprocess_region(data, "vertical")

        super().__init__(data, edge_width=edge_width, z_index=z_index, dims_order=dims_order, ndisplay=ndisplay)
        self.name = "vertical"


class Horizontal(Rectangle):
    """Class for horizontal region"""

    def __init__(
        self,
        data,
        *,
        edge_width=1,
        z_index=0,
        dims_order=None,
        ndisplay=2,
    ):
        if len(data) ==2:
            data = preprocess_region(data, "horizontal")

        super().__init__(data, edge_width=edge_width, z_index=z_index, dims_order=dims_order, ndisplay=ndisplay)
        self.name = "horizontal"
