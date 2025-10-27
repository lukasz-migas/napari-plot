"""Infinite region"""

from __future__ import annotations

import typing as ty
import warnings
from copy import copy

import numpy as np
from napari.layers.base import no_op
from napari.layers.shapes._shapes_utils import create_box
from napari.layers.utils.color_transformations import (
    ColorType,
    normalize_and_broadcast_colors,
    transform_color,
    transform_color_with_defaults,
)
from napari.utils.events import Event
from napari.utils.misc import ensure_iterable

from napari_plot.layers.base import BaseLayer
from napari_plot.layers.region._region import region_classes
from napari_plot.layers.region._region_constants import Box, Mode, Orientation
from napari_plot.layers.region._region_list import InfiniteRegionList
from napari_plot.layers.region._region_mouse_bindings import (
    add,
    edit,
    highlight,
    move,
    select,
)
from napari_plot.layers.region._region_utils import (
    get_default_region_type,
    parse_infinite_region_orientation,
)

REV_TOOL_HELP = {
    "Hold <space> to pan/zoom, select region by clicking on it and then move mouse left-right or up-down": {
        Mode.MOVE
    },
    "Hold <space> to pan/zoom, drag along x-axis (horizontal); drag along y-axis (vertical)": {
        Mode.ADD
    },
    "Hold <space> to pan/zoom, select region by clicking on it and then drag left-right or up-down": {
        Mode.EDIT
    },
    "Hold <space> to pan/zoom, press <backspace> to remove selected": {Mode.SELECT},
    "Enter a selection mode to edit region properties": {Mode.PAN_ZOOM},
    "Enter transformation mode": {Mode.TRANSFORM},
}
TOOL_HELP = {}
for t, modes in REV_TOOL_HELP.items():
    for m in modes:
        TOOL_HELP[m] = t


class Region(BaseLayer):
    """Regions layer.

    Parameters
    ----------
    data : list of array-like or list of tuple of array-like and str or list of tuple of array-like and Orientation
        Layer can be initialized by providing list of arrays, list of arrays + orientation of region where each
        array has two elements (start position, end position).
    orientation : str or list of str or list of Orientation
        List of orientations for each provided region. If orientations are not provided, they will be inferred directly
        from `data` or using the default of `vertical`.
    color : str, array-like
        If string can be any color name recognized by vispy or hex value if starting with `#`. If array-like must
        be 1-dimensional array with 3 or 4 elements. If a list is supplied it must be the same length as the length of
        `data` and each element will be applied to each region otherwise the same value will be used for all regions.
    z_index : int or list
        Specifier of z order priority. Regions with higher z order are displayed on top of others. If a list is
        supplied it must be the same length as the length of `data` and each element will be applied to each region
        otherwise the same value will be used for all regions.
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
        Mode.PAN_ZOOM: no_op,
        Mode.TRANSFORM: no_op,
        Mode.ADD: add,
        Mode.SELECT: select,
        Mode.MOVE: move,
        Mode.EDIT: edit,
    }
    _move_modes = {
        Mode.PAN_ZOOM: no_op,
        Mode.TRANSFORM: no_op,
        Mode.ADD: no_op,
        Mode.SELECT: highlight,
        Mode.MOVE: highlight,
        Mode.EDIT: no_op,
    }
    _double_click_modes = {
        Mode.PAN_ZOOM: no_op,
        Mode.TRANSFORM: no_op,
        Mode.ADD: no_op,
        Mode.SELECT: no_op,
        Mode.MOVE: no_op,
        Mode.EDIT: no_op,
    }
    _cursor_modes = {
        Mode.PAN_ZOOM: "standard",
        Mode.TRANSFORM: "standard",
        Mode.ADD: "pointing",
        Mode.SELECT: "pointing",
        Mode.MOVE: "pointing",
        Mode.EDIT: "standard",
    }

    _highlight_color = (0, 0.6, 1, 0.5)
    _highlight_width = 1.5

    # If more shapes are present then they are randomly sub-sampled in the thumbnail
    _max_regions_thumbnail = 10

    def __init__(
        self,
        data=None,
        *,
        # napari-plot parameters
        orientation="vertical",
        color=(1.0, 1.0, 1.0, 1.0),
        z_index=0,
        # napari parameters
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
        data, orientation = parse_infinite_region_orientation(data, orientation)
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
            current_color=Event,
            highlight=Event,
            shifted=Event,
            accept=Event,
            selected=Event,
            adding=Event,
            removed=Event,
        )

        # Data container
        self._data_view = InfiniteRegionList()
        self._ndisplay_stored = self._slice_input.ndisplay
        self._display_order_stored = []

        self._selected_box = None
        # indices of selected regions
        self._value = (None, None)
        self._value_stored = (None, None)
        self._selected_data = set()
        self._selected_data_stored = set()
        # responsible for handling selection box
        self._is_selecting = False
        self._drag_start = None
        self._drag_box = None
        self._drag_box_stored = None
        # responsible for handling creation of new infinite line
        self._is_moving = False
        self._moving_coordinates = None
        self._moving_value = (None, None)
        # responsible for handling creation of new infinite line
        self._is_creating = False
        self._creating_value: tuple[
            ty.Optional[tuple[float, float]], ty.Optional[Orientation]
        ] = (None, None)

        self._init_regions(data, orientation=orientation, color=color, z_index=z_index)
        # set the current_* properties
        if len(data) > 0:
            self._current_color = self.color[-1]
        elif len(data) == 0:
            self._current_color = transform_color_with_defaults(
                num_entries=1, colors=color, elem_name="color", default="black"
            )
        self.visible = visible

    def accept(self):
        """Emit accept event"""
        self.events.accept()

    def add(self, data, *, orientation="vertical", color=None, z_index=None):
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
        data, shape_type = parse_infinite_region_orientation(data, orientation)

        n_new_shapes = len(data)
        if color is None:
            color = self._get_new_color(n_new_shapes)
        if self._data_view is not None:
            z_index = z_index or max(self._data_view._z_index, default=-1) + 1
        else:
            z_index = z_index or 0

        if n_new_shapes > 0:
            self._add_regions(
                data, orientation=orientation, color=color, z_index=z_index
            )
            self.events.data(value=self.data)

    def move(
        self,
        index: int,
        new_data: tuple[float, float],
        orientation=None,
        finished: bool = False,
    ):
        """Move region to new location"""
        self._data_view.edit(index, data=new_data, new_orientation=orientation)
        self._emit_new_data()
        if finished:
            self.events.shifted(index=index)

    def _add_move(self, pos: tuple[float, float], *, orientation="vertical"):
        """Add a new line at the clicked position."""
        self._is_creating = True
        self._creating_value = (pos, orientation)
        self.events.adding()

    def _add_finish(
        self, pos, *, orientation="vertical", color=None, z_index=None
    ) -> int:
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

    def _init_regions(self, data, *, orientation=None, color=None, z_index=None):
        """Add regions to the data view."""
        n_regions = len(data)
        color = self._initialize_color(color, n_regions=n_regions)
        with self.block_thumbnail_update():
            self._add_regions(
                data,
                orientation=orientation,
                color=color,
                z_index=z_index,
            )
            self._data_view._update_z_order()

    def _add_regions(
        self,
        data,
        *,
        orientation="vertical",
        color=None,
        z_index=None,
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
            transformed_fc = transform_color_with_defaults(
                num_entries=len(data),
                colors=color,
                elem_name="color",
                default="white",
            )
            transformed_color = normalize_and_broadcast_colors(
                len(data), transformed_fc
            )

            # Turn input arguments into iterables
            region_inputs = zip(
                data,
                ensure_iterable(orientation),
                transformed_color,
                ensure_iterable(z_index),
            )
            self._add_region_to_view(region_inputs, self._data_view)

        self._display_order_stored = copy(self._slice_input.order)
        self._ndisplay_stored = copy(self._slice_input.ndisplay)
        self._update_dims()

    @staticmethod
    def _add_region_to_view(shape_inputs, data_view):
        """Build new region and add them to the _data_view"""
        for d, ot, fc, z in shape_inputs:
            region_cls = region_classes[Orientation(ot)]
            region = region_cls(d, z_index=z)
            # Add region
            data_view.add(region, color=fc, z_refresh=False)
        data_view._update_z_order()

    @property
    def n_regions(self) -> int:
        """Get number of regions."""
        return len(self._data_view.regions)

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
        mode = self._mode_setter_helper(mode)
        if mode == self._mode:
            return

        assert mode is not None, mode
        old_mod = self._mode

        if mode == Mode.SELECT:
            self.selected_data = set()

        self.help = TOOL_HELP[mode]
        if mode != Mode.SELECT or old_mod != Mode.SELECT:
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

        # Update properties based on selected shapes
        if len(selected_data) > 0:
            selected_data_indices = list(selected_data)
            selected_colors = self.color[selected_data_indices]
            colors = np.unique(selected_colors, axis=0)
            if len(colors) == 1:
                self.current_color = colors[0]
        self.events.selected()

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
    def color(self):
        """(N x 4) np.ndarray: Array of RGBA colors for each region."""
        return self._data_view.color

    @color.setter
    def color(self, color):
        """Set the color property

        Parameters
        ----------
        color : (N, 4) array or str
            The value for setting color
        """
        if len(self.data) > 0:
            transformed_color = transform_color_with_defaults(
                num_entries=len(self.data),
                colors=color,
                elem_name="color",
                default="white",
            )
            colors = normalize_and_broadcast_colors(len(self.data), transformed_color)
        else:
            colors = np.empty((0, 4))

        self._data_view.color = colors
        self.events.color()
        self._update_thumbnail()

    @property
    def current_color(self):
        """Return current color."""
        return self._current_color

    @current_color.setter
    def current_color(self, color: ColorType):
        self._current_color = transform_color(color)[0]
        if self._update_properties:
            for i in self.selected_data:
                self._data_view.update_color(i, self._current_color)
                self.events.color()
            self._update_thumbnail()
        self.events.current_color()

    @staticmethod
    def _initialize_color(color, n_regions: int):
        """Get the colors the Region layer will be initialized with

        Parameters
        ----------
        color : (N, 4) array or str
            The value for color
        n_regions : int
            Number of regions to be initialized.

        Returns
        -------
        init_colors : (N, 4) array or str
            The calculated values for setting color
        """
        if n_regions > 0:
            transformed_color = transform_color_with_defaults(
                num_entries=n_regions, colors=color, elem_name="color", default="white"
            )
            init_colors = normalize_and_broadcast_colors(n_regions, transformed_color)
        else:
            init_colors = np.empty((0, 4))
        return init_colors

    def _get_state(self):
        """Get dictionary of layer state"""
        state = self._get_base_state()
        state.update({"data": self.data, "color": self.color, "label": self.label})
        return state

    def _update_thumbnail(self):
        """Update thumbnail with current data"""
        # don't update the thumbnail if dragging a shape
        if self._is_moving is False and self._allow_thumbnail_update is True:
            thumbnail = np.zeros(self._thumbnail_shape)
            # # calculate min vals for the vertices and pad with 0.5
            # # the offset is needed to ensure that the top left corner of the shapes
            # # corresponds to the top left corner of the thumbnail
            # de = self._extent_data
            # offset = np.array([de[0, d] for d in self._slice_input.displayed]) + 0.5
            # # calculate range of values for the vertices and pad with 1
            # # padding ensures the entire shape can be represented in the thumbnail
            # # without getting clipped
            # with warnings.catch_warnings():
            #     warnings.filterwarnings("ignore", "invalid value encountered in cast")
            #     shape = np.ceil([de[1, d] - de[0, d] + 1 for d in self._slice_input.displayed]).astype(int)
            # with warnings.catch_warnings():
            #     warnings.filterwarnings("ignore", "divide by zero")
            #     zoom_factor = np.divide(self._thumbnail_shape[:2], shape[-2:]).min()
            #
            # color_mapped = self._data_view.to_colors(
            #     colors_shape=self._thumbnail_shape[:2],
            #     zoom_factor=zoom_factor,
            #     offset=offset[-2:],
            #     max_shapes=self._max_regions_thumbnail,
            # )
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
    def data(self):
        """Return data"""
        return self._data_view.data

    @data.setter
    def data(self, data):
        data, orientation = parse_infinite_region_orientation(data)
        n_new_regions = len(data)
        if orientation is None:
            orientation = self.orientation
        colors = self._data_view.color
        z_indices = self._data_view.z_indices

        # fewer shapes, trim attributes
        if self.n_regions > n_new_regions:
            orientation = orientation[:n_new_regions]
            z_indices = z_indices[:n_new_regions]
            colors = colors[:n_new_regions]
        # more shapes, add attributes
        elif self.n_regions < n_new_regions:
            n_shapes_difference = n_new_regions - self.n_regions
            orientation = (
                orientation
                + [get_default_region_type(orientation)] * n_shapes_difference
            )
            z_indices = z_indices + [0] * n_shapes_difference
            colors = np.concatenate((colors, self._get_new_color(n_shapes_difference)))
        # create new instance of the data
        self._data_view = InfiniteRegionList()
        self.add(data, orientation=orientation, color=colors, z_index=z_indices)

        self._update_dims()
        self.events.data(value=self.data)
        self._on_editable_changed()

    @property
    def z_index(self) -> ty.List[int]:
        """list of int: z_index for each shape."""
        return self._data_view.z_indices

    @z_index.setter
    def z_index(self, z_index: ty.Union[int, ty.List[int]]):
        """Set z_index of shape using either int or list of int.

        When list of int is provided, must be of equal length to n shapes.

        Parameters
        ----------
        z_index : int or list of int
            z-index of shapes
        """
        if isinstance(z_index, list):
            if not len(z_index) == self.n_regions:
                raise ValueError(
                    "Length of list does not match number of orientations."
                )
            z_indices = z_index
        elif isinstance(z_index, int):
            z_indices = [z_index for _ in range(self.n_regions)]
        else:
            z_indices = [z_index for _ in range(self.n_regions)]
        for i, z_idx in enumerate(z_indices):
            self._data_view.update_z_index(i, z_idx)

    @property
    def orientation(self):
        """Orientation of the infinite region."""
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

    def _set_view_slice(self):
        self.events.set_data()

    def _get_value(self, position):
        """Value of the data at a position in data coordinates"""
        coord = position[0:2]

        # Check selected region
        value = None
        if value is None:
            # Check if mouse inside shape
            region = self._data_view.inside(coord)
            value = (region, None)
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
        return extrema.astype(float)

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

    def move_to_front(self):
        """Moves selected objects to be displayed in front of all others."""
        if len(self.selected_data) == 0:
            return
        new_z_index = max(self._data_view._z_index) + 1
        for index in self.selected_data:
            self._data_view.update_z_index(index, new_z_index)
        self.refresh()

    def move_to_back(self):
        """Moves selected objects to be displayed behind all others."""
        if len(self.selected_data) == 0:
            return
        new_z_index = min(self._data_view._z_index) - 1
        for index in self.selected_data:
            self._data_view.update_z_index(index, new_z_index)
        self.refresh()

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

    # def interaction_box(self, index):
    #     """Create the interaction box around a shape or list of shapes.
    #     If a single index is passed then the bounding box will be inherited
    #     from that shapes interaction box. If list of indices is passed it will
    #     be computed directly.
    #
    #     Parameters
    #     ----------
    #     index : int | list | set | EventedSet
    #         Index of a single shape, or a list of shapes around which to
    #         construct the interaction box
    #
    #     Returns
    #     -------
    #     box : np.ndarray
    #         9x2 array of vertices of the interaction box. The first 8 points
    #         are the corners and midpoints of the box in clockwise order
    #         starting in the upper-left corner. The 9th point is the center of
    #         the box.
    #     """
    #     if isinstance(index, (list, np.ndarray, set, EventedSet)):
    #         if len(index) == 0:
    #             box = None
    #         elif len(index) == 1:
    #             box = copy(self._data_view.regions[next(iter(index))]._box)
    #         else:
    #             indices = np.isin(self._data_view.displayed_index, list(index))
    #             box = create_box(self._data_view.displayed_vertices[indices])
    #     else:
    #         box = copy(self._data_view.regions[index]._box)
    #     return box
    #
    # def _highlight_regions(self):
    #     """Find outlines of any selected or hovered regions.
    #
    #     Returns
    #     -------
    #     vertices : None | np.ndarray
    #         Nx2 array of any vertices of outline or None
    #     triangles : None | np.ndarray
    #         Mx3 array of any indices of vertices for triangles of outline or
    #         None
    #     """
    #     if self._value is not None and (self._value[0] is not None or len(self.selected_data) > 0):
    #         if len(self.selected_data) > 0:
    #             index = list(self.selected_data)
    #             if self._value[0] is not None:
    #                 if self._value[0] in index:
    #                     pass
    #                 else:
    #                     index.append(self._value[0])
    #             index.sort()
    #         else:
    #             index = self._value[0]
    #
    #         centers, offsets, triangles = self._data_view.highlight(index)
    #         vertices = centers + (self.scale_factor * self._highlight_width * offsets)
    #         vertices = vertices[:, ::-1]
    #     else:
    #         vertices = None
    #         triangles = None
    #     return vertices, triangles
