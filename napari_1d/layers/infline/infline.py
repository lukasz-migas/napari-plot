"""Infinite region"""
import typing as ty
from contextlib import contextmanager
from copy import copy

import numpy as np
from napari.layers.base import Layer, no_op
from napari.layers.shapes._shapes_utils import create_box
from napari.layers.utils.color_transformations import (
    ColorType,
    normalize_and_broadcast_colors,
    transform_color,
    transform_color_with_defaults,
)
from napari.utils.events import Event
from napari.utils.misc import ensure_iterable

from ._infline import infline_classes
from ._infline_constants import Box, Mode, Orientation
from ._infline_list import InfiniteLineList
from ._infline_mouse_bindings import add, highlight, move, select
from ._infline_utils import extract_inf_line_orientation, get_default_infline_type


class InfLine(Layer):
    """InfLine layer"""

    _drag_modes = {Mode.ADD: add, Mode.SELECT: select, Mode.PAN_ZOOM: no_op, Mode.MOVE: move}
    _move_modes = {Mode.ADD: no_op, Mode.SELECT: highlight, Mode.PAN_ZOOM: no_op, Mode.MOVE: no_op}
    _cursor_modes = {
        Mode.ADD: "standard",
        Mode.SELECT: "standard",
        Mode.PAN_ZOOM: "standard",
        Mode.MOVE: "cross",
    }

    _highlight_color = (0, 0.6, 1)
    _highlight_width = 1.5

    def __init__(
        self,
        data,
        *,
        orientation="vertical",
        label="",
        color="red",
        width=1,
        z_index=0,
        # base parameters
        name=None,
        metadata=None,
        scale=None,
        translate=None,
        rotate=None,
        shear=None,
        affine=None,
        opacity=1.0,
        blending="translucent",
        visible=True,
    ):
        # sanitize data
        if data is None:
            data = np.asarray([])
        else:
            data, orientation = extract_inf_line_orientation(data, orientation)
            data = np.asarray(data, dtype=np.float64)
        super().__init__(
            data,
            ndim=2,
            name=name,
            metadata=metadata,
            scale=scale,
            translate=translate,
            rotate=rotate,
            shear=shear,
            affine=affine,
            opacity=opacity,
            blending=blending,
            visible=visible,
        )
        self.events.add(
            color=Event, width=Event, label=Event, mode=Event, shifted=Event, highlight=Event, current_color=Event
        )
        # Flag set to false to block thumbnail refresh
        self._allow_thumbnail_update = True

        if not len(data) == len(orientation):
            raise ValueError("The number of points and orientations is incorrect. They must be matched.")

        self._label = label
        self._width = width
        self._data_view = InfiniteLineList()

        # each line can have its own color
        self._color = transform_color(color)

        # indices of selected lines
        self._value = (None, None)
        self._value_stored = (None, None)
        self._selected_data = set()
        self._selected_data_stored = set()
        self._selected_box = None

        self._drag_start = None
        self._drag_box = None
        self._drag_box_stored = None
        self._is_creating = False
        self._is_selecting = False
        self._moving_coordinates = None
        self._is_moving = False
        self._moving_value = (None, None)

        # change mode once to trigger the Mode setting logic
        self._mode = Mode.PAN_ZOOM
        self.mode = Mode.PAN_ZOOM
        self._status = self.mode

        self._init_lines(
            data,
            orientation=orientation,
            color=color,
            z_index=z_index,
        )

        # set the current_* properties
        if len(data) > 0:
            self._current_color = self.color[-1]
        else:
            self._current_color = transform_color_with_defaults(
                num_entries=1,
                colors=color,
                elem_name="color",
                default="white",
            )

        self.visible = visible

    def _init_lines(self, data, *, orientation=None, color=None, z_index=None):
        """Add regions to the data view."""
        n = len(data)
        color = self._initialize_color(color, n_lines=n)
        with self.block_thumbnail_update():
            self._add_line(
                data,
                orientation=orientation,
                color=color,
                z_index=z_index,
                z_refresh=False,
            )
            self._data_view._update_z_order()

    def _add_line(
        self,
        data,
        *,
        orientation="vertical",
        color=None,
        z_index=None,
        z_refresh=True,
    ):
        """Add shapes to the data view.

        Parameters
        ----------
        data : Array | Tuple(Array,str) | List[Array | Tuple(Array, str)] | Tuple(List[Array], str)
            List of shape data, where each element is either an (N, D) array of the
            N vertices of a shape in D dimensions or a tuple containing an array of
            the N vertices and the shape_type string. When a shape_type is present,
            it overrides keyword arg shape_type. Can be an 3-dimensional array
            if each shape has the same number of vertices.
        orientation : string | list
            String of orientation type, must be one of "{'vertical', 'horizontal'}.
            If list is supplied it must be the same length as the length of `data`
            and each element will be applied to each region otherwise the same
            value will be used for all regions. Override by data orientation, if present.
        color : str | tuple | list
            If string can be any color name recognized by vispy or hex value if
            starting with `#`. If array-like must be 1-dimensional array with 3
            or 4 elements. If a list is supplied it must be the same length as
            the length of `data` and each element will be applied to each shape
            otherwise the same value will be used for all shapes.
        z_index : int | list
            Specifier of z order priority. Shapes with higher z order are
            displayed on top of others. If a list is supplied it must be the
            same length as the length of `data` and each element will be
            applied to each shape otherwise the same value will be used for all
            shapes.
        z_refresh : bool
            If set to true, the mesh elements are re-indexed with the new z order.
            When shape_index is provided, z_refresh will be overwritten to false,
            as the z indices will not change.
            When adding a batch of shapes, set to false  and then call
            ShapesList._update_z_order() once at the end.
        """
        if color is None:
            color = self._current_color
        if self._data_view is not None:
            z_index = z_index or max(self._data_view._z_index, default=-1) + 1
        else:
            z_index = z_index or 0

        if len(data) > 0:
            # transform the colors
            transformed_c = transform_color_with_defaults(
                num_entries=len(data),
                colors=color,
                elem_name="color",
                default="white",
            )
            transformed_color = normalize_and_broadcast_colors(len(data), transformed_c)

            # Turn input arguments into iterables
            region_inputs = zip(
                data,
                ensure_iterable(orientation),
                transformed_color,
                ensure_iterable(z_index),
            )
            self._add_line_to_view(region_inputs, self._data_view)

        self._display_order_stored = copy(self._dims_order)
        self._ndisplay_stored = copy(self._ndisplay)
        self._update_dims()

    def _add_line_to_view(self, infline_inputs, data_view):
        """Build new region and add them to the _data_view"""
        for d, ot, c, z in infline_inputs:
            infline_cls = infline_classes[Orientation(ot)]
            region = infline_cls(d, z_index=z)

            # Add region
            data_view.add(region, color=c, z_refresh=False)
        data_view._update_z_order()

    # noinspection PyMethodMayBeStatic
    def _initialize_color(self, color, n_lines: int):
        """Get the face colors the Shapes layer will be initialized with

        Parameters
        ----------
        color : (N, 4) array or str
            The value for setting edge or face_color
        n_lines : int
            Number of lines to be initialized.

        Returns
        -------
        init_colors : (N, 4) array or str
            The calculated values for setting edge or face_color
        """
        if n_lines > 0:
            transformed_color = transform_color_with_defaults(
                num_entries=n_lines,
                colors=color,
                elem_name="color",
                default="white",
            )
            init_colors = normalize_and_broadcast_colors(n_lines, transformed_color)
        else:
            init_colors = np.empty((0, 4))
        return init_colors

    @property
    def mode(self) -> str:
        """str: Interactive mode

        Interactive mode. The normal, default mode is PAN_ZOOM, which
        allows for normal interactivity with the canvas.

        In MOVE the region is moved to new location
        """
        return str(self._mode)

    @mode.setter
    def mode(self, mode):
        mode, changed = self._mode_setter_helper(mode, Mode)
        if not changed:
            return

        assert mode is not None, mode
        old_mode = self._mode

        if mode == Mode.SELECT:
            self.selected_data = set()

        if mode == Mode.PAN_ZOOM:
            self.help = ""
        else:
            self.help = "Hold <space> to pan/zoom."

        if mode != Mode.SELECT or old_mode != Mode.SELECT:
            self._selected_data_stored = set()

        self._mode = mode
        self._set_highlight()
        self.events.mode(mode=mode)

    @property
    def selected_data(self) -> set:
        """set: set of currently selected points."""
        return self._selected_data

    @selected_data.setter
    def selected_data(self, selected_data):
        self._selected_data = set(selected_data)
        self._selected_box = self.interaction_box(self._selected_data)

        # Update properties based on selected shapes
        if len(selected_data) > 0:
            selected_data_indices = list(selected_data)
            selected_face_colors = self._color[selected_data_indices]
            face_colors = np.unique(selected_face_colors, axis=0)
            if len(face_colors) == 1:
                face_color = face_colors[0]
                self.current_color = face_color

    @property
    def current_color(self):
        """Get current color."""
        return self._current_color

    @current_color.setter
    def current_color(self, color: ColorType):
        """Update current color."""
        self._current_color = transform_color(color)[0]

        # update properties
        if self._update_properties:
            for i in self.selected_data:
                self._color[i] = self._current_color
                self.events.color()
            self._update_thumbnail()
        self.events.current_color()

    def _get_ndim(self) -> int:
        """Determine number of dimensions of the layer"""
        return 2

    def _get_state(self):
        """Get dictionary of layer state"""
        state = self._get_base_state()
        state.update({"data": self.data, "color": self.color, "label": self.label})
        return state

    def _update_thumbnail(self):
        """Update thumbnail with current data"""
        colormapped = np.zeros(self._thumbnail_shape)
        colormapped[..., 3] = 1
        colormapped[14:18] = (1.0, 1.0, 1.0, 1.0)
        colormapped[:, 14:18] = (1.0, 1.0, 1.0, 1.0)
        colormapped[..., 3] *= self.opacity
        self.thumbnail = colormapped

    @property
    def _view_data(self) -> np.ndarray:
        """Get the coords of the points in view

        Returns
        -------
        view_data : (N x D) np.ndarray
            Array of coordinates for the N points in view
        """
        return self.data

    @property
    def data(self) -> np.ndarray:
        """Return data"""
        return self._data_view.data

    @data.setter
    def data(self, data):
        data, orientation = extract_inf_line_orientation(data)
        n_new_regions = len(data)
        if orientation is None:
            orientation = self.orientation

        color = self._data_view.color
        z_indices = self._data_view.z_indices

        # fewer shapes, trim attributes
        if self.n_regions > n_new_regions:
            orientation = orientation[:n_new_regions]
            z_indices = z_indices[:n_new_regions]
            color = color[:n_new_regions]
        # more shapes, add attributes
        elif self.n_regions < n_new_regions:
            n_shapes_difference = n_new_regions - self.n_regions
            orientation = orientation + [get_default_infline_type(orientation)] * n_shapes_difference
            z_indices = z_indices + [0] * n_shapes_difference
            color = np.concatenate((color, self._get_new_color(n_shapes_difference)))
        self._data_view = InfiniteLineList()
        self.add(data, orientation=orientation, color=color, z_index=z_indices)

        self._update_dims()
        self.events.data(value=self.data)
        self._set_editable()

    @property
    def orientations(self) -> ty.List[Orientation]:
        return self._data_view.orientations

    def add(
        self,
        data,
        *,
        orientation="vertical",
        color=None,
        z_index=None,
    ):
        """Add shapes to the current layer.

        Parameters
        ----------
        data : Array | Tuple(Array,str) | List[Array | Tuple(Array, str)] | Tuple(List[Array], str)
            List of shape data, where each element is either an (N, D) array of the
            N vertices of a shape in D dimensions or a tuple containing an array of
            the N vertices and the shape_type string. When a shape_type is present,
            it overrides keyword arg shape_type. Can be an 3-dimensional array
            if each shape has the same number of vertices.
        orientation : string | list
            String of orientation type, must be one of "{'vertical', 'horizontal'}.
            If list is supplied it must be the same length as the length of `data`
            and each element will be applied to each region otherwise the same
            value will be used for all regions. Override by data orientation, if present.
        color : str | tuple | list
            If string can be any color name recognized by vispy or hex value if
            starting with `#`. If array-like must be 1-dimensional array with 3
            or 4 elements. If a list is supplied it must be the same length as
            the length of `data` and each element will be applied to each shape
            otherwise the same value will be used for all shapes.
        z_index : int | list
            Specifier of z order priority. Shapes with higher z order are
            displayed on top of others. If a list is supplied it must be the
            same length as the length of `data` and each element will be
            applied to each shape otherwise the same value will be used for all
            shapes.
        """
        data, orientation = extract_inf_line_orientation(data, orientation)

        n_new_shapes = len(data)
        if color is None:
            color = self._get_new_color(n_new_shapes)
        if self._data_view is not None:
            z_index = z_index or max(self._data_view._z_index, default=-1) + 1
        else:
            z_index = z_index or 0

        if n_new_shapes > 0:
            self._add_line(
                data,
                orientation=orientation,
                color=color,
                z_index=z_index,
            )
            self.events.data(value=self.data)

    def _add_creating(self, pos, *, orientation="vertical", color=None, z_index=None) -> int:
        """Add line while return the count."""
        self.add(
            [pos],
            orientation=[orientation],
            color=[color] if color is not None else color,
            z_index=[z_index] if z_index is not None else z_index,
        )
        return len(self.data) - 1

    def move(self, index: int, data: float, orientation=None, finished: bool = False):
        """Move region to new location"""
        if index > len(self.data):
            raise ValueError("Selected index is larger than total number of elements.")
        self._data_view.edit(index, data=data, new_orientation=orientation)
        self._emit_new_data()
        if finished:
            self.events.shifted()

    def _emit_new_data(self):
        self._update_dims()
        self.events.data(value=self.data)
        self._set_editable()

    def _get_new_color(self, adding: int):
        """Get the color for the shape(s) to be added.

        Parameters
        ----------
        adding : int
            the number of shapes that were added
            (and thus the number of color entries to add)

        Returns
        -------
        new_colors : (N, 4) array
            (Nx4) RGBA array of colors for the N new shapes
        """
        new_colors = np.tile(self._current_color, (adding, 1))
        return new_colors

    @property
    def color(self) -> np.ndarray:
        """Get color"""
        return self._data_view.color

    @color.setter
    def color(self, color):
        self._data_view.color = color
        self.events.color()
        self._update_thumbnail()

    @property
    def label(self):
        """Get label"""
        return self._label

    @label.setter
    def label(self, value):
        self._label = value
        self.events.label()

    @property
    def width(self):
        """Get width"""
        return self._width

    @width.setter
    def width(self, value: float):
        self._width = value
        self.events.width()

    def _set_view_slice(self):
        self.events.set_data()

    def _get_value(self, position):
        """Value of the data at a position in data coordinates"""
        coord = position[0:2]

        # Check selected region
        value = None
        if value is None:
            # Check if mouse inside shape
            infline = self._data_view.inside(coord)
            value = (infline, None)
        return value

    @property
    def _extent_data(self) -> np.ndarray:
        return np.full((2, 2), np.nan)

    def _set_highlight(self, force=False):
        """Render highlights.

        Parameters
        ----------
        force : bool
            Bool that forces a redraw to occur when `True`.
        """
        # Check if any shape or vertex ids have changed since last call
        if (
            self.selected_data == self._selected_data_stored
            and np.all(self._value == self._value_stored)
            and np.all(self._drag_box == self._drag_box_stored)
        ) and not force:
            return
        self._selected_data_stored = copy(self.selected_data)
        self._value_stored = copy(self._value)
        self._drag_box_stored = copy(self._drag_box)
        self.events.highlight()

    def interaction_box(self, index):
        """Create the interaction box around a shape or list of shapes.
        If a single index is passed then the bounding box will be inherited
        from that shapes interaction box. If list of indices is passed it will
        be computed directly.
        Parameters
        ----------
        index : int | list
            Index of a single shape, or a list of shapes around which to
            construct the interaction box
        Returns
        -------
        box : np.ndarray
            10x2 array of vertices of the interaction box. The first 8 points
            are the corners and midpoints of the box in clockwise order
            starting in the upper-left corner. The 9th point is the center of
            the box, and the last point is the location of the rotation handle
            that can be used to rotate the box
        """
        box = None
        # if isinstance(index, (list, np.ndarray, set)):
        #     if len(index) == 0:
        #         box = None
        #     elif len(index) == 1:
        #         box = copy(self._data_view.regions[list(index)[0]]._box)
        #     else:
        #         indices = np.isin(self._data_view.displayed_index, list(index))
        #         box = create_box(self._data_view.displayed_vertices[indices])
        # else:
        #     box = copy(self._data_view.regions[index]._box)
        #
        # if box is not None:
        #     rot = box[Box.TOP_CENTER]
        #     length_box = np.linalg.norm(box[Box.BOTTOM_LEFT] - box[Box.TOP_LEFT])
        #     if length_box > 0:
        #         r = self._rotation_handle_length * self.scale_factor
        #         rot = rot - r * (box[Box.BOTTOM_LEFT] - box[Box.TOP_LEFT]) / length_box
        #     box = np.append(box, [rot], axis=0)
        return box

    @contextmanager
    def block_thumbnail_update(self):
        """Use this context manager to block thumbnail updates"""
        self._allow_thumbnail_update = False
        yield
        self._allow_thumbnail_update = True

    def _compute_vertices_and_box(self):
        """Compute location of highlight vertices and box for rendering.

        Returns
        -------
        vertices : np.ndarray
            Nx2 array of any vertices to be rendered as Markers
        face_color : str
            String of the face color of the Markers
        edge_color : str
            String of the edge color of the Markers and Line for the box
        pos : np.ndarray
            Nx2 array of vertices of the box that will be rendered using a
            Vispy Line
        width : float
            Width of the box edge
        """
        if self._is_selecting:
            # If currently dragging a selection box just show an outline of
            # that box
            edge_color = self._highlight_color
            box = create_box(self._drag_box)
            # Use a subset of the vertices of the interaction_box to plot
            # the line around the edge
            pos = box[Box.LINE][:, ::-1]
        else:
            # Otherwise show nothing
            edge_color = "white"
            pos = None
        return edge_color, pos
