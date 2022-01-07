"""Infinite line list."""
import typing as ty

import numpy as np

from ..utilities import make_infinite_line, make_infinite_pos
from ._infline import InfiniteLine, infline_classes
from ._infline_constants import Orientation


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

    @property
    def lines(self) -> np.ndarray:
        """Return array of lines to be rendered."""
        return make_infinite_line(self.data, self.orientations, self.color)

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
            self.update_color(i, col, update=False)

    def update_color(self, index, color, update=True):
        """Updates the face color of a single shape located at index.

        Parameters
        ----------
        index : int
            Location in list of the shape to be changed.
        color : str | tuple
            If string can be any color name recognized by vispy or hex value if
            starting with `#`. If array-like must be 1-dimensional array with 3
            or 4 elements.
        update : bool
            If True, update the mesh with the new color property. Set to False to avoid
            repeated updates when modifying multiple shapes. Default is True.
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

    def inside(self, coord, max_dist: float = 5.0):
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


def nearby_line(distance, max_dist: float):
    """Returns mask of nearest elements and if they meet the distance criteria."""
    return np.where(np.any(np.abs(distance) < max_dist, axis=1))[0]


def lines_intersect_box(lines, corners):
    """Return indices of lines that intersect with the box."""
    y, x = corners[:, 0], corners[:, 1]
    ymin, ymax = np.min(y), np.max(y)
    xmin, xmax = np.min(x), np.max(x)

    # check whether any x-axis elements are between the x-min, x-max
    x_mask = np.logical_and(lines[:, 0] > xmin, lines[:, 0] < xmax)
    y_mask = np.logical_and(lines[:, 1] > ymin, lines[:, 1] < ymax)
    return np.where(np.logical_or(x_mask, y_mask))[0]
