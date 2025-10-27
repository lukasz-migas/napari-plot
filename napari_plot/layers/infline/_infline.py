"""Infinite line."""

from napari_plot.layers.infline._infline_constants import Orientation


class InfiniteLine:
    """Line."""

    _data: float

    def __init__(self, data: float, orientation: Orientation, z_index: int = 0):
        self.name = ""
        self.data = data
        self.orientation = orientation
        self.z_index = z_index

    def __repr__(self) -> str:
        return f"{self.name}<{self.data:.2f}>"

    @property
    def data(self) -> float:
        """Return data."""
        return self._data

    @data.setter
    def data(self, value: float) -> None:
        self._data = value

    @property
    def z_index(self) -> int:
        """int: z order priority of shape. Shapes with higher z order displayed on top of others."""
        return self._z_index

    @z_index.setter
    def z_index(self, z_index: int) -> None:
        self._z_index = z_index


class VerticalLine(InfiniteLine):
    """Vertical infinite line."""

    def __init__(self, data: float, z_index: int = 0):
        super().__init__(data, Orientation.VERTICAL, z_index=z_index)
        self.name = "Vertical"


class HorizontalLine(InfiniteLine):
    """Horizontal infinite line."""

    def __init__(self, data: float, z_index: int = 0):
        super().__init__(data, Orientation.HORIZONTAL, z_index=z_index)
        self.name = "Horizontal"


infline_classes = {
    Orientation.HORIZONTAL: HorizontalLine,
    Orientation.VERTICAL: VerticalLine,
}
