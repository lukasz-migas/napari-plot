"""MultiLine layer."""

import numpy as np
from napari.layers.utils.color_transformations import (
    ColorType,
    normalize_and_broadcast_colors,
    transform_color_with_defaults,
)
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import Event

from napari_plot.layers.base import BaseLayer
from napari_plot.layers.multiline._multiline_constants import Method
from napari_plot.layers.multiline._multiline_list import MultiLineList
from napari_plot.layers.multiline._multiline_utils import parse_multiline_data


class MultiLine(BaseLayer):
    """MultiLine layer

    Parameters
    ----------
    data : dict of xs and ys array (N, 1), (N, D), optional
        Coordinates for N points in 2 dimensions.
    color : str, array-like
        If string can be any color name recognized by vispy or hex value if starting with `#`. If array-like must
        be 1-dimensional array with 3 or 4 elements.
    width : float
        Width of the line in pixel units.
    method : str or Method
        Rendering method. Either `gl` or `agg`.
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

    def __init__(
        self,
        data,
        *,
        # napari-plot parameters
        color=(1.0, 1.0, 1.0, 1.0),
        width=2,
        method="gl",
        label="",
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
        data = parse_multiline_data(data)

        super().__init__(
            data,
            label=label,
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
        self.events.add(color=Event, width=Event, method=Event, highlight=Event, stream=Event)
        # Flag set to false to block thumbnail refresh
        self._allow_thumbnail_update = True

        self._data_view = MultiLineList()

        self._width = width
        self._method = Method(method)

        self._init_lines(data, color=color)

        # set the current_* properties
        if len(data[0]) > 0:
            self._current_color = self.color[-1]
        else:
            self._current_color = transform_color_with_defaults(
                num_entries=1,
                colors=color,
                elem_name="color",
                default="white",
            )
        self.visible = visible

    def _init_lines(self, data, *, color=None):
        """Add lines to the data view."""
        xs, ys = data
        n = len(ys)
        color = self._initialize_color(color, n_lines=n)
        with self.block_thumbnail_update():
            self._add_line(xs, ys, color=color)

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

    def add(self, data, *, color=None):
        """Add line(s) to the container."""
        xs, ys = parse_multiline_data(data)
        n_new = len(ys)
        if color is None:
            color = self._get_new_color(n_new)
        if n_new > 0:
            self._add_line(xs, ys, color=color)

    def _add_line(self, xs, ys, *, color=None):
        """Add lines to data view.

        Parameters
        ----------
        xs : list of np.ndarray
            List of x-axis arrays.
        ys : list of np.ndarray
            List of y-axis arrays.
        color : iterable of str | tuple | np.ndarray, optional
            Iterable of colors for each line. If value is not provided then default color is used instead.
            If the color is a single entry, then all lines will have the same color. If the color is iterable of colors
            then those will be used instead.
        """
        if color is None:
            color = self._current_color

        if len(ys) > 0:
            # transform the colors
            transformed_c = transform_color_with_defaults(
                num_entries=len(ys),
                colors=color,
                elem_name="color",
                default="white",
            )
            transformed_color = normalize_and_broadcast_colors(len(ys), transformed_c)
            self._data_view.add(xs, ys, transformed_color)

    @property
    def color(self) -> np.ndarray:
        """Get color."""
        return self._data_view.color

    @color.setter
    def color(self, color):
        self._data_view.color = color
        self.events.color()
        self._update_thumbnail()

    def update_color(self, index: int, color: np.ndarray):
        """Update color of single line.

        Parameters
        ----------
        index : int
            Index of the line to update the color of.
        color : str | tuple | np.ndarray
            Color of the line.
        """
        self._data_view.update_color(index, color)
        self.events.color()
        self._update_thumbnail()

    def _get_new_color(self, adding: int):
        """Get the color for the shape(s) to be added.

        Parameters
        ----------
        adding : int
            The number of new lines that were added (and thus the number of entries to add)

        Returns
        -------
        new_colors : (N, 4) array
            (Nx4) RGBA array of colors for the N new lines
        """
        new_colors = np.tile(self._current_color, (adding, 1))
        return new_colors

    def _update_thumbnail(self):
        """Update thumbnail with current data"""
        if self._allow_thumbnail_update:
            h = self._thumbnail_shape[0]
            thumbnail = np.zeros(self._thumbnail_shape)
            thumbnail[..., 3] = 1
            thumbnail[h - 2 : h + 2, :] = 1  # horizontal stripe
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
    def data(self, value):
        data = parse_multiline_data(value)
        self._data_view = MultiLineList()
        self.add(data)
        self._emit_new_data()

    def stream(self, data, full_update: bool = False):
        """Rapidly update data on the layer without doing additional checks.

        This method will simply replace the existing data with new without checking e.g. the number of lines or the
        number of colors. This validation falls to the user to ensure that data is correct.

        This method only triggers the `stream` event which will update the line data without updating line connections
        or colors.
        """
        xs, ys = parse_multiline_data(data)
        self._data_view.xs = xs
        self._data_view.ys = ys
        self.events.stream() if not full_update else self._emit_new_data()

    @property
    def width(self) -> float:
        """Get width"""
        return self._width

    @width.setter
    def width(self, value: float):
        self._width = value
        self.events.width()

    @property
    def method(self) -> Method:
        """Get method"""
        return self._method

    @method.setter
    def method(self, value):
        self._method = value
        self.events.method()

    @property
    def current_color(self):
        """Get current color."""
        return self._current_color

    @current_color.setter
    def current_color(self, color: ColorType):
        """Update current color."""
        self._current_color = transform_color(color)[0]
        self.events.current_color()

    def _set_view_slice(self):
        self.events.set_data()

    def _get_value(self, position):
        """Value of the data at a position in data coordinates"""
        return position[1]

    @property
    def _extent_data(self) -> np.ndarray:
        return self._data_view.extent_data

    def _get_state(self):
        """Get dictionary of layer state"""
        state = self._get_base_state()
        state.update(
            {
                "width": self.width,
                "method": self.method,
                "label": self.label,
            }
        )
        return state
