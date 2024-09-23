"""Infinite line list."""

import typing as ty

import numpy as np

from napari_plot.layers.infline._infline import InfiniteLine, infline_classes
from napari_plot.layers.infline._infline_constants import Orientation
from napari_plot.layers.infline._infline_utils import (
    lines_intersect_box,
    make_infinite_color,
    make_infinite_line,
    make_infinite_pos,
    nearby_line,
)


class InfiniteLineList:
    """List of lines class.

    Parameters
    ----------
    data : list
        List of Shape objects
    """

    def __init__(self, data=(), ndisplay=2):
        self._ndisplay = ndisplay

        self.inflines: ty.List[InfiniteLine] = []
        self._z_index = np.empty(0, dtype=int)
        self._z_order = np.empty(0, dtype=int)
        self._color = np.empty((0, 4))

        for d in data:
            self.add(d)

    @property
    def data(self):
        """list of (M, D) array: data arrays for each shape."""
        return np.asarray([s.data for s in self.inflines])

    def get_display_lines(self, indices=None):
        """Return data to be displayed."""
        return make_infinite_line(self.data, self.orientations, self.color, indices=indices)

    @property
    def orientations(self):
        """list of str: shape types for each shape."""
        return [s.orientation for s in self.inflines]

    @property
    def z_indices(self) -> ty.List[int]:
        """list of int: z-index for each shape."""
        return [s.z_index for s in self.inflines]

    @property
    def color(self):
        """(N x 4) np.ndarray: Array of RGBA face colors for each shape"""
        return self._color

    @color.setter
    def color(self, color):
        self._set_color(color)

    def get_display_color(self):
        """Get display color."""
        return make_infinite_color(self.color)

    def _set_color(self, colors):
        """Set the face_color or edge_color property

        Parameters
        ----------
        colors : (N, 4) np.ndarray
            The value for setting edge or face_color. There must
            be one color for each shape
        """
        n_lines = len(self.data)
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
        color : str | tuple
            If string can be any color name recognized by vispy or hex value if
            starting with `#`. If array-like must be 1-dimensional array with 3
            or 4 elements.
        """
        self._color[index] = color

    def add(self, infline, color=None, index=None, z_refresh: bool = False):
        """Adds a single InfiniteLine object"""
        if not isinstance(infline, InfiniteLine):
            raise ValueError("Region must be a class of Rectangle")

        if index is None:
            # index = len(self.inflines)
            self.inflines.append(infline)
            self._z_index = np.append(self._z_index, infline.z_index)

            if color is None:
                color = np.array([1, 1, 1, 1])
            self._color = np.vstack([self._color, color])
        else:
            z_refresh = False
            self.inflines[index] = infline
            self._z_index[index] = infline.z_index

        if z_refresh:
            # Set z_order
            self._update_z_order()

    def edit(self, index, data, color=None, new_orientation=None):
        """Update the data of a single shape located at index."""
        if new_orientation is not None:
            cur_line = self.inflines[index]
            if isinstance(new_orientation, (str, Orientation)):
                orientation = Orientation(new_orientation)
                if orientation in infline_classes.keys():
                    line_cls = infline_classes[orientation]
                else:
                    raise ValueError(
                        f"{orientation} must be one of {infline_classes}",
                    )
            else:
                line_cls = infline_classes
            infline = line_cls(
                data,
                z_index=cur_line.z_index,
            )
        else:
            infline = self.inflines[index]
            infline.data = data

        if color is not None:
            self._color[index] = color

        self.add(infline, index=index)
        self._update_z_order()

    def remove_all(self):
        """Removes all shapes"""
        self.inflines = []
        self._z_index = np.empty(0, dtype=int)
        self._z_order = np.empty(0, dtype=int)
        self._color = np.empty((0, 4))

    def remove(self, index, renumber=True):
        """Removes a single shape located at index.

        Parameters
        ----------
        index : int
            Location in list of the shape to be removed.
        renumber : bool
            Bool to indicate whether to renumber all shapes or not. If not the
            expectation is that this shape is being immediately added back to the
            list using `add`.
        """
        self.inflines.pop(index)
        self._color = np.delete(self._color, index, axis=0)
        self._z_index = np.delete(self._z_index, index)
        self._z_order = np.delete(self._z_order, index)

        if renumber:
            self._update_z_order()

    def _update_z_order(self):
        """Updates the z order of the triangles given the z_index list"""
        self._z_order = np.argsort(self._z_index)

    def inside(self, coord, max_dist: float = 0.1):
        """Determine if any line at given coord by looking at nearest line within defined limit."""
        pos = make_infinite_pos(self.data, self.orientations)
        indices = nearby_line(pos - coord[::-1], max_dist)
        if len(indices) > 0:
            z_list = [self._z_order[i] for i in indices]
            return indices[np.argsort(z_list)][0]

    def lines_in_box(self, corners):
        """Determines which lines, if any, are inside an axis aligned box."""
        pos = make_infinite_pos(self.data, self.orientations)
        indices = lines_intersect_box(pos, corners)
        return indices
