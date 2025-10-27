"""Infinite line list."""

from __future__ import annotations

import typing as ty

import numpy as np

from napari_plot.layers.region._region import InfiniteRegion, region_classes
from napari_plot.layers.region._region_constants import Orientation
from napari_plot.layers.region._region_utils import (
    make_infinite_region_color,
    make_infinite_region_mean,
    make_infinite_region_pos,
    make_infinite_region_simple_data,
    region_intersect_box,
)


class InfiniteRegionList:
    """List of lines class.

    Parameters
    ----------
    data : list
        List of Shape objects
    """

    def __init__(self, data=(), ndisplay=2):
        self._ndisplay = ndisplay

        self.regions: ty.List[InfiniteRegion] = []
        self._z_index = np.empty(0, dtype=int)
        self._z_order = np.empty(0, dtype=int)
        self._color = np.empty((0, 4))

        for d in data:
            self.add(d)

    @property
    def data(self):
        """list of (M, D) array: data arrays for each shape."""
        return np.asarray([s.data for s in self.regions])

    def get_display_pos(self, indices=None):
        """Return position of lines."""
        return make_infinite_region_pos(self.data, self.orientations, indices=indices)

    def get_simple_lines_and_colors(self, indices=None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return position and color of infinite lines."""
        return make_infinite_region_simple_data(self.data, self.orientations, self.color, indices=indices)

    @property
    def orientations(self):
        """list of str: shape types for each shape."""
        return [s.orientation for s in self.regions]

    @property
    def z_indices(self) -> ty.List[int]:
        """list of int: z-index for each shape."""
        return [s.z_index for s in self.regions]

    @property
    def color(self):
        """(N x 4) np.ndarray: Array of RGBA face colors for each shape"""
        return self._color

    @color.setter
    def color(self, color):
        self._set_color(color)

    def get_display_color(self):
        """Get display color."""
        return make_infinite_region_color(self.color)

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

    def add(self, region, color=None, index=None, z_refresh: bool = False):
        """Adds a single InfiniteLine object"""
        if not isinstance(region, InfiniteRegion):
            raise TypeError("Region must be a class of Rectangle")

        if index is None:
            self.regions.append(region)
            self._z_index = np.append(self._z_index, region.z_index)

            if color is None:
                color = np.array([1, 1, 1, 1])
            self._color = np.vstack([self._color, color])
        else:
            z_refresh = False
            self.regions[index] = region
            self._z_index[index] = region.z_index

        if z_refresh:
            # Set z_order
            self._update_z_order()

    def edit(self, index, data, color=None, new_orientation=None):
        """Update the data of a single shape located at index."""
        if new_orientation is not None:
            cur_line = self.regions[index]
            if isinstance(new_orientation, (str, Orientation)):
                orientation = Orientation(new_orientation)
                if orientation in region_classes:
                    region_cls = region_classes[orientation]
                else:
                    raise ValueError(
                        f"{orientation} must be one of {region_classes}",
                    )
            else:
                region_cls = orientation
            region = region_cls(data, z_index=cur_line.z_index)
        else:
            region = self.regions[index]
            region.data = data

        if color is not None:
            self._color[index] = color

        self.add(region, index=index)
        self._update_z_order()

    def remove_all(self):
        """Removes all shapes"""
        self.regions = []
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
        self.regions.pop(index)
        self._color = np.delete(self._color, index, axis=0)
        self._z_index = np.delete(self._z_index, index)
        self._z_order = np.delete(self._z_order, index)

        if renumber:
            self._update_z_order()

    def _update_z_order(self):
        """Updates the z order of the triangles given the z_index list"""
        self._z_order = np.argsort(self._z_index)

    def update_z_index(self, index: int, z_index: int) -> None:
        """Update the z-index of a single shape located at index.

        Parameters
        ----------
        index : int
            Location in list of the shape to be changed.
        z_index : int
            The new z-index for the shape.
        """
        self._z_index[index] = int(z_index)
        self._update_z_order()

    def inside(self, coord, max_dist: float = 0.1):
        """Determine if any line at given coord by looking at nearest line within defined limit."""
        # pos = make_infinite_line_pos(self.data, self.orientations)
        # with suppress(IndexError):
        #     indices = nearby_line(pos - coord[::-1], max_dist)
        #     if len(indices) > 0:
        #         z_list = [self._z_order[i] for i in indices]
        #         return indices[np.argsort(z_list)][0]
        return

    def regions_in_box(self, corners):
        """Determines which lines, if any, are inside an axis aligned box."""
        pos = make_infinite_region_mean(self.data, self.orientations)
        indices = region_intersect_box(pos, corners)
        return indices
