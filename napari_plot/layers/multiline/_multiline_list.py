"""Container class for MultiLine data."""

import typing as ty

import numpy as np

from napari_plot.layers.multiline._multiline_utils import (
    get_data_limits,
    make_multiline_color,
    make_multiline_line,
    make_multiline_pos,
)


class MultiLineList:
    """Multi-line class."""

    def __init__(self):
        self._data = {"xs": [], "ys": []}
        self._color = np.empty((0, 4))

    def add(self, xs: ty.List, ys: ty.List[np.ndarray], color: np.ndarray):
        """Add data to store."""
        if len(ys) != len(color):
            raise ValueError(
                "The number of `ys` must be equal to the number of colors."
            )
        if len(xs) == 0 and self.n_lines == 0:
            raise ValueError("Cannot add `ys` to empty container.")

        # check if adding data to existing stores
        if self.n_lines > 0:
            if self.xs_equal_ys:
                if len(xs) != len(ys) and len(xs) > 0:
                    raise ValueError(
                        "Cannot add `xs` and `ys` arrays that are not of equal length if what is already present has"
                        " equal number of arrays."
                    )
            else:
                if len(xs) > 0:
                    raise ValueError(
                        "Cannot add `xs` and `ys` arrays to layer that does not have equal number of `xs` and `ys`."
                    )

        # make sure tha xs is iterable
        if len(xs) == 0:
            xs = [None] * len(ys)
        elif len(xs) == 1 and len(ys) > 1:
            xs.extend([None] * (len(ys) - 1))
        for x, y, _color in zip(xs, ys, color):
            self._add(x, y, _color)

    def _add(self, x, y, color):
        """Append data to containers."""
        if x is not None:
            self._data["xs"].append(x)
        self._data["ys"].append(y)
        if color is None:
            color = np.array([1, 1, 1, 1])
        self._color = np.vstack([self._color, color])

    @property
    def n_lines(self) -> int:
        """Return the number of lines."""
        return len(self._data["ys"])

    @property
    def xs_equal_ys(self) -> bool:
        """Flag that indicates whether there is equal number of `x` and `y` arrays."""
        return len(self._data["xs"]) == len(self._data["ys"])

    @property
    def xs(self) -> ty.List[np.ndarray]:
        """Get x-axis arrays."""
        return self._data["xs"]

    @xs.setter
    def xs(self, value):
        self._data["xs"] = value

    @property
    def ys(self) -> ty.List[np.ndarray]:
        """Get y-axis arrays."""
        return self._data["ys"]

    @ys.setter
    def ys(self, value):
        self._data["ys"] = value

    @property
    def data(self):
        """Return nicely formatted data."""
        return

    @property
    def extent_data(self) -> np.ndarray:
        """Get data extents."""
        return get_data_limits(self.xs, self.ys)

    def get_display_data(self):
        """Return data in a manner that can be understood by vispy Line visual."""
        return make_multiline_pos(self.xs, self.ys)

    def get_display_lines(self):
        """Return data in a manner that can be understood by vispy Line visual."""
        return make_multiline_line(self.xs, self.ys, self.color)

    def get_display_color(self):
        """Return color."""
        return make_multiline_color(self.ys, self.color)

    @property
    def color(self):
        """(N x 4) np.ndarray: Array of RGBA face colors for each shape"""
        return self._color

    @color.setter
    def color(self, color):
        self._set_color(color)

    def _set_color(self, colors):
        """Set the face_color or edge_color property

        Parameters
        ----------
        colors : (N, 4) np.ndarray
            The value for setting edge or face_color. There must
            be one color for each shape
        """
        n_lines = self.n_lines
        if not np.all(colors.shape == (n_lines, 4)):
            raise ValueError(
                f"color must have shape ({n_lines}, 4)",
            )

        for i, col in enumerate(colors):
            self.update_color(i, col)

    def update_color(self, index, color):
        """Updates the face color of a single shape located at index.

        Parameters
        ----------
        index : int
            Location in list of the shape to be changed.
        color : str | tuple | np.ndarray
            If string can be any color name recognized by vispy or hex value if
            starting with `#`. If array-like must be 1-dimensional array with 3
            or 4 elements.
        """
        self._color[index] = color
