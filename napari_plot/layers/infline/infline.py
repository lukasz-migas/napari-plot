"""Infinite region"""

import typing as ty
import warnings
from copy import copy

import numpy as np
from napari.layers.base import no_op
from napari.layers.base._base_mouse_bindings import (
    highlight_box_handles,
    transform_with_box,
)
from napari.layers.utils.color_transformations import (
    ColorType,
    normalize_and_broadcast_colors,
    transform_color,
    transform_color_with_defaults,
)
from napari.utils.events import Event
from napari.utils.misc import ensure_iterable

from napari_plot.layers.base import BaseLayer
from napari_plot.layers.infline._infline import infline_classes
from napari_plot.layers.infline._infline_constants import Box, Mode, Orientation
from napari_plot.layers.infline._infline_list import InfiniteLineList
from napari_plot.layers.infline._infline_mouse_bindings import add, highlight, move, select
from napari_plot.layers.infline._infline_utils import (
    get_default_infline_type,
    parse_infline_orientation,
)

REV_TOOL_HELP = {
    "Hold <space> to pan/zoom, select line by clicking on it and then move mouse left-right or up-down.": {Mode.MOVE},
    "Hold <space> to pan/zoom, hold <ctrl> or drag along y-axis (vertical line), hold <shift> or drag along x-axis"
    " (horizontal line)": {Mode.ADD},
    "Hold <space> to pan/zoom, press <backspace> to remove selected": {Mode.SELECT},
    "Enter a selection mode to edit region properties": {Mode.PAN_ZOOM},
    "Enter transformation mode": {Mode.TRANSFORM},
}
TOOL_HELP = {}
for t, modes in REV_TOOL_HELP.items():
    for m in modes:
        TOOL_HELP[m] = t


class InfLine(BaseLayer):
    """InfLine layer

    Parameters
    ----------
    data :
        Coordinates for N points in 2 dimensions.
    orientation : str or Orientation or list of str or list of Orientation
        If string, can be `vertical` or `horizontal`. If a list is supplied it must have the same length as the length
        of the `data` and each element will be applied to each infinite line otherwise the same value will be used for
        all lines.
    color : str, array-like
        If string can be any color name recognized by vispy or hex value if starting with `#`. If array-like must
        be 1-dimensional array with 3 or 4 elements.
    width : float
        Width of the line in pixel units.
    label : str
        Label to be displayed in the plot legend. (unused at the moment)
    name : str
        Name of the layer.
    metadata : dict
        Layer metadata.
    scale : tuple of float
        Scale factors for the layer.
    translate : tuple of float
        Translation values for the layer.
    rotate : float, 3-tuple of float, or n-D array.
        If a float convert into a 2D rotation matrix using that value as an angle. If 3-tuple convert into a 3D
        rotation matrix, using a yaw, pitch, roll convention. Otherwise assume an nD rotation. Angles are assumed
        to be in degrees. They can be converted from radians with np.degrees if needed.
    shear : 1-D array or n-D array
        Either a vector of upper triangular values, or an nD shear matrix with ones along the main diagonal.
    affine : n-D array or napari.utils.transforms.Affine
        (N+1, N+1) affine transformation matrix in homogeneous coordinates. The first (N, N) entries correspond to a
        linear transform and the final column is a length N translation vector and a 1 or a napari `Affine` transform
        object. Applied as an extra transform on top of the provided scale, rotate, and shear values.
    opacity : float
        Opacity of the layer visual, between 0.0 and 1.0.
    blending : str
        One of a list of preset blending modes that determines how RGB and alpha values of the layer visual get mixed.
        Allowed values are {'opaque', 'translucent', 'translucent_no_depth', and 'additive'}.
    visible : bool
        Whether the layer visual is currently being displayed.
    """

    _modeclass = Mode
    _drag_modes = {
        Mode.ADD: add,
        Mode.SELECT: select,
        Mode.PAN_ZOOM: no_op,
        Mode.MOVE: move,
        Mode.TRANSFORM: transform_with_box,
    }
    _move_modes = {
        Mode.ADD: no_op,
        Mode.SELECT: highlight,
        Mode.PAN_ZOOM: no_op,
        Mode.MOVE: highlight,
        Mode.TRANSFORM: highlight_box_handles,
    }
    _cursor_modes = {
        Mode.ADD: "standard",
        Mode.SELECT: "standard",
        Mode.PAN_ZOOM: "standard",
        Mode.MOVE: "cross",
        Mode.TRANSFORM: "standard",
    }

    _highlight_color = (0, 0.6, 1, 0.5)
    _highlight_width = 3

    def __init__(
        self,
        data=None,
        *,
        orientation="vertical",
        color=(1.0, 1.0, 1.0, 1.0),
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
        data, orientation = parse_infline_orientation(data, orientation)
        if not len(data) == len(orientation):
            raise ValueError("The number of points and orientations is incorrect. They must be matched.")

        super().__init__(
            data,
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
            color=Event,
            width=Event,
            shifted=Event,
            highlight=Event,
            current_color=Event,
            selected=Event,
            adding=Event,
            removed=Event,
        )

        self._width = width
        self._data_view = InfiniteLineList()

        # indices of selected lines
        self._value = (None, None)
        self._value_stored = (None, None)
        self._selected_data = set()
        self._selected_data_stored = set()

        self._ndisplay_stored = self._slice_input.ndisplay

        # responsible for handling selection box
        self._is_selecting = False
        self._drag_start = None
        self._drag_box = None
        self._drag_box_stored = None
        # responsible for handling moving of infinite line
        self._is_moving = False
        self._moving_coordinates = None
        self._moving_value = (None, None)
        # responsible for handling creation of new infinite line
        self._is_creating = False
        self._creating_value: tuple[ty.Optional[float], ty.Optional[Orientation]] = (None, None)

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

    def add(self, data, *, orientation="vertical", color=None, z_index=None):
        """Add lines to the current layer.

        Parameters
        ----------
        data : Array | Tuple(float,str) | List[float | Tuple(float, str)] | Tuple(List[float], str)
            List of line data, where each element is either position or a tuple containing (position, orientation).
            When orientation is present, it overrides keyword argument `orientation`.
        orientation : string | list
            String of orientation type, must be one of "{'vertical', 'horizontal'}. If list is supplied it must be the
            same length as the length of `data` and each element will be applied to each region otherwise the same
            value will be used for all regions. Override by data orientation, if present.
        color : str | tuple | list
            If string can be any color name recognized by vispy or hex value if starting with `#`. If array-like must
            be 1-dimensional array with 3 or 4 elements. If a list is supplied it must be the same length as the length
            of `data` and each element will be applied to each shape otherwise the same value will be used for all
            lines.
        z_index : int | list
            Specifier of z order priority. Lines with higher z order are displayed on top of others. If a list is
            supplied it must be the same length as the length of `data` and each element will be applied to each shape
            otherwise the same value will be used for all shapes.
        """
        data, orientation = parse_infline_orientation(data, orientation)

        n_new = len(data)
        if color is None:
            color = self._get_new_color(n_new)
        if self._data_view is not None:
            z_index = z_index or max(self._data_view._z_index, default=-1) + 1
        else:
            z_index = z_index or 0

        if n_new > 0:
            self._add_line(
                data,
                orientation=orientation,
                color=color,
                z_index=z_index,
            )
            self.events.data(value=self.data)

    def _add_move(self, pos: float, *, orientation="vertical"):
        """Add a new line at the clicked position."""
        self._is_creating = True
        self._creating_value = (pos, orientation)
        self.events.adding()

    def _add_finish(self, pos, *, orientation="vertical", color=None, z_index=None) -> int:
        self.add(
            [pos],
            orientation=[orientation],
            color=[color] if color is not None else color,
            z_index=[z_index] if z_index is not None else z_index,
        )
        self._is_creating = False
        self._creating_value = (None, None)
        self.events.adding()
        return len(self.data) - 1

    def _add_creating(self, pos, *, orientation="vertical", color=None, z_index=None) -> int:
        """Add new line and return the index of said line.

        Parameters
        ----------
        pos : float
            Position along the x-axis or y-axis.
        orientation : str or Orientation
            String of orientation type, must be one of "{'vertical', 'horizontal'}.
        color : str or tuple or list or array, optional
            If string can be any color name recognized by vispy or hex value if starting with `#`. If array-like must
            be 1-dimensional array with 3 or 4 elements.
        z_index : int, optional
            Specifier of z order priority. Lines with higher z order are displayed on top of others.

        Returns
        -------
        index : int
            Index of the just added line.
        """
        self.add(
            [pos],
            orientation=[orientation],
            color=[color] if color is not None else color,
            z_index=[z_index] if z_index is not None else z_index,
        )
        return len(self.data) - 1

    def move(self, index: int, pos: float, orientation=None, finished: bool = False):
        """Move line to new location.

        Parameters
        ----------
        index : int
            Index of the line.
        pos : float
            New position along the x-axis or y-axis.
        orientation : str or Orientation, optional
            String of orientation type, must be one of "{'vertical', 'horizontal'}. If one is not provided, only the
            position is changed.
        finished : bool
            Flag to indicate whether the `shifted` events should be emitted.
        """
        if index > len(self.data):
            raise ValueError("Selected index is larger than total number of elements.")
        self._data_view.edit(index, data=pos, new_orientation=orientation)
        self._emit_new_data()
        if finished:
            self.events.shifted(index=index)

    def _init_lines(self, data, *, orientation=None, color=None, z_index=None):
        """Add lines to the data view."""
        n = len(data)
        color = self._initialize_color(color, n_lines=n)
        with self.block_thumbnail_update():
            self._add_line(
                data,
                orientation=orientation,
                color=color,
                z_index=z_index,
            )
            self._data_view._update_z_order()

    def _add_line(
        self,
        data,
        *,
        orientation="vertical",
        color=None,
        z_index=None,
    ):
        """Add lines to the data view.

        Parameters
        ----------
        data : Array | Tuple(float,str) | List[float | Tuple(float, str)] | Tuple(List[float], str)
            List of line data, where each element is either position or a tuple containing (position, orientation).
            When orientation is present, it overrides keyword argument `orientation`.
        orientation : string | list
            String of orientation type, must be one of "{'vertical', 'horizontal'}. If list is supplied it must be the
            same length as the length of `data` and each element will be applied to each region otherwise the same
            value will be used for all regions. Override by data orientation, if present.
        color : str | tuple | list
            If string can be any color name recognized by vispy or hex value if starting with `#`. If array-like must
            be 1-dimensional array with 3 or 4 elements. If a list is supplied it must be the same length as the length
            of `data` and each element will be applied to each shape otherwise the same value will be used for all
            lines.
        z_index : int | list
            Specifier of z order priority. Lines with higher z order are displayed on top of others. If a list is
            supplied it must be the same length as the length of `data` and each element will be applied to each shape
            otherwise the same value will be used for all shapes.
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

        self._display_order_stored = copy(self._slice_input.order)
        self._ndisplay_stored = self._slice_input.ndisplay
        self._update_dims()

    @staticmethod
    def _add_line_to_view(infline_inputs, data_view):
        """Build new region and add them to the _data_view"""
        for d, ot, c, z in infline_inputs:
            infline_cls = infline_classes[Orientation(ot)]
            infline = infline_cls(d, z_index=z)

            # Add region
            data_view.add(infline, color=c, z_refresh=False)
        data_view._update_z_order()

    @staticmethod
    def _initialize_color(color, n_lines: int):
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
    def mode(self, mode: ty.Union[str, Mode]):
        mode: Mode = self._mode_setter_helper(mode)
        if mode == self._mode:
            return

        assert mode is not None, mode
        old_mode = self._mode

        if mode == Mode.SELECT:
            self.selected_data = set()

        self.help = TOOL_HELP[str(mode)]

        if mode != Mode.SELECT or old_mode != Mode.SELECT:
            self._selected_data_stored = set()

        self._mode = mode
        self._set_highlight()
        self.events.mode(mode=mode)

    @property
    def n_inflines(self) -> int:
        """Get number of infinite lines."""
        return len(self._data_view.inflines)

    @property
    def selected_data(self) -> set:
        """set: set of currently selected points."""
        return self._selected_data

    @selected_data.setter
    def selected_data(self, selected_data):
        self._selected_data = set(selected_data)

        # Update properties based on selected shapes
        if len(selected_data) > 0:
            selected_data_indices = list(selected_data)
            selected_colors = self.color[selected_data_indices]
            colors = np.unique(selected_colors, axis=0)
            if len(colors) == 1:
                self.current_color = colors[0]
        self.events.selected()

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
                self._data_view.update_color(i, self._current_color)
                self.events.color()
            self._update_thumbnail()
        self.events.current_color()

    def _get_state(self):
        """Get dictionary of layer state"""
        state = self._get_base_state()
        state.update({"data": self.data, "color": self.color, "label": self.label})
        return state

    def _update_thumbnail(self):
        """Update thumbnail with current data"""
        if self._is_moving is False and self._allow_thumbnail_update is True:
            thumbnail = np.zeros(self._thumbnail_shape)
            thumbnail[..., 3] = 1
            thumbnail[14:18] = (1.0, 1.0, 1.0, 1.0)
            thumbnail[:, 14:18] = (1.0, 1.0, 1.0, 1.0)
            thumbnail[..., 3] *= self.opacity
            self.thumbnail = thumbnail

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
        data, orientation = parse_infline_orientation(data)
        n_new = len(data)
        if orientation is None:
            orientation = self.orientation

        color = self._data_view.color
        z_indices = self._data_view.z_indices

        # fewer shapes, trim attributes
        if self.n_inflines > n_new:
            orientation = orientation[:n_new]
            z_indices = z_indices[:n_new]
            color = color[:n_new]
        # more shapes, add attributes
        elif self.n_inflines < n_new:
            n_shapes_difference = n_new - self.n_inflines
            orientation = orientation + [get_default_infline_type(orientation)] * n_shapes_difference
            z_indices = z_indices + [0] * n_shapes_difference
            color = np.concatenate((color, self._get_new_color(n_shapes_difference)))
        self._data_view = InfiniteLineList()
        self.add(data, orientation=orientation, color=color, z_index=z_indices)

        self._update_dims()
        self.events.data(value=self.data)
        self._on_editable_changed()

    @property
    def orientation(self) -> ty.List[Orientation]:
        """Return list of orientations."""
        return self._data_view.orientations

    def remove_selected(self):
        """Remove any selected shapes."""
        index = list(self.selected_data)
        to_remove = sorted(index, reverse=True)
        for ind in to_remove:
            self._data_view.remove(ind)
        self.events.removed(value=to_remove)
        self.selected_data = set()
        self._emit_new_data()

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
        self._set_color(color)
        self._update_thumbnail()

    def _set_color(self, color):
        """Set the face_color property

        Parameters
        ----------
        color : (N, 4) array or str
            The value for setting edge or face_color
        """
        if len(self.data) > 0:
            transformed_color = transform_color_with_defaults(
                num_entries=len(self.data), colors=color, elem_name="color", default="white"
            )
            colors = normalize_and_broadcast_colors(len(self.data), transformed_color)
        else:
            colors = np.empty((0, 4))

        self._data_view.color = colors
        self.events.color()

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
        coord = position[0:2]  # always two-d so two coordinates needed

        # Check selected region
        value = None
        if value is None:
            # Check if mouse inside shape
            infline = self._data_view.inside(coord)
            value = (infline, None)
        return value

    @property
    def _extent_data(self) -> np.ndarray:
        if len(self.data) == 0:
            extrema = np.full((2, 2), np.nan)
        else:
            pos = self._data_view.get_display_pos()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                maxs = np.nanmax(pos, axis=0)[::-1]
                mins = np.nanmin(pos, axis=0)[::-1]
                extrema = np.vstack([mins, maxs])
        return extrema

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

    def _compute_box(self) -> tuple[ty.Union[str, np.ndarray], np.ndarray, float]:
        """Compute location of highlight vertices and box for rendering.

        Returns
        -------
        edge_color : np.ndarray
            String of the edge color of the Markers and Line for the box
        pos : np.ndarray
            Nx2 array of vertices of the box that will be rendered using a
            Vispy Line
        width : int
            Width of the line
        """
        from napari.layers.shapes._shapes_utils import create_box

        if self._is_selecting:
            # If currently dragging a selection box just show an outline of # that box
            edge_color = self._highlight_color
            box = create_box(self._drag_box)
            # Use a subset of the vertices of the interaction_box to plot
            # the line around the edge
            pos = box[Box.LINE][:, ::-1]
        else:
            # Otherwise show nothing
            edge_color = np.array([0, 0, 0, 0])
            pos = None
        return edge_color, pos, self._highlight_width
