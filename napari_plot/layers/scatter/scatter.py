"""Scatter points layer"""
import typing as ty
from copy import deepcopy

import numpy as np
from napari.layers.points._points_constants import SYMBOL_ALIAS, Symbol
from napari.layers.utils.color_transformations import normalize_and_broadcast_colors, transform_color_with_defaults
from napari.layers.utils.layer_utils import dataframe_to_properties
from napari.layers.utils.text_manager import TextManager
from napari.utils.events import Event

from ..base import BaseLayer


class Scatter(BaseLayer):
    """Scatter layer

    Parameters
    ----------
    data : array (N, 2)
        Coordinates for N points in 2 dimensions.
    symbol : str or Symbol
        Symbol to be used for the point markers. Must be one of the following: arrow, clobber, cross, diamond, disc,
        hbar, ring, square, star, tailed_arrow, triangle_down, triangle_up, vbar, x.
    text : str, dict
        Text to be displayed with the points. If text is set to a key in properties, the value of that property will be
        displayed. Multiple properties can be composed using f-string-like syntax
        (e.g., '{property_1}, {float_property:.2f}). A dictionary can be provided with keyword arguments to set the
        text values and display properties. See TextManager.__init__() for the valid keyword arguments.
        For example usage, see /napari/examples/add_points_with_text.py.
    face_color : str, array-like
        Color of the point marker body. Numeric color values should be RGB(A). Input will be broadcasted to (N, 4)
        array.
    edge_color : str, array-like
        Color of the point marker border. Numeric color values should be RGB(A). Input will be broadcasted to (N, 4)
        array.
    edge_width : int, float, array-like
        Width of the symbol edge in pixels.
    edge_width_is_relative : bool
        If enabled, edge_width is interpreted as a fraction of the point size.
    size : float, array
        Size of the point marker in data pixels. If given as a scalar, all points are made the same size. If given as
        an array, size must be the same or broadcastable to the same shape as the data.
    scaling : bool
        Toggle to either enable or disable auto-scaling of the points.
    properties : dict {str: array (N,)}, DataFrame
        Properties for each point. Each property should be an array of length N, where N is the number of points.
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

    # The max number of points that will ever be used to render the thumbnail
    # If more points are present then they are randomly sub-sampled
    _max_points_thumbnail = 1024

    _default_face_color = np.array((1.0, 1.0, 1.0, 1.0), dtype=np.float32)
    _default_edge_color = np.array((1.0, 1.0, 1.0, 1.0), dtype=np.float32)
    _default_edge_width = 1
    _default_size = 1
    _default_rel_size = 0.1

    def __init__(
        self,
        data,
        *,
        # napari-plot parameters
        symbol="o",
        text=None,
        face_color=(1.0, 1.0, 1.0, 1.0),
        edge_width=0.1,
        edge_width_is_relative=True,
        edge_color=(1.0, 0.0, 0.0, 1.0),
        size=1,
        scaling=True,
        properties=None,
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
        if data is None:
            data = np.empty((0, 2))
        else:
            data = np.asarray(data)
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
        self.events.add(
            size=Event,
            symbol=Event,
            face_color=Event,
            edge_width=Event,
            edge_color=Event,
            edge_width_is_relative=Event,
            properties=Event,
            scaling=Event,
        )

        # add data
        self._data = data
        self._symbol = symbol
        self._face_color = self._initialize_color(face_color, "edge", len(self._data))
        self._edge_color = self._initialize_color(edge_color, "face", len(self._data))
        self._scaling = scaling
        self._edge_width_is_relative = edge_width_is_relative

        # Save the properties
        if properties is None:
            properties = {}
            self._properties = properties
            self._property_choices = properties
        elif len(data) > 0:
            properties, _ = dataframe_to_properties(properties)
            self._properties = self._validate_properties(properties)
            self._property_choices = {k: np.unique(v) for k, v in properties.items()}
        elif len(data) == 0:
            self._property_choices = {k: np.asarray(v) for k, v in properties.items()}
            empty_properties = {k: np.empty(0, dtype=v.dtype) for k, v in self._property_choices.items()}
            self._properties = empty_properties

        # make the text
        if text is None or isinstance(text, (list, np.ndarray, str)):
            self._text = TextManager(text, len(data), self.properties)
        elif isinstance(text, dict):
            copied_text = deepcopy(text)
            copied_text["properties"] = self.properties
            copied_text["n_text"] = len(data)
            self._text = TextManager(**copied_text)
        else:
            raise TypeError("text should be a string, array, or dict")
        with self.events.blocker_all():
            self.edge_width = edge_width
            self.size = size
        self.visible = visible

    @staticmethod
    def _initialize_color(color, attribute: str, n_points: int):
        """Get the face/edge colors the Scatter layer will be initialized with

        Parameters
        ----------
        color : (N, 4) array or str
            The value for setting edge or face_color
        attribute : str in {'edge', 'face'}
            The name of the attribute to set the color of. Should be 'edge' for edge_color or 'face' for face_color.

        Returns
        -------
        init_colors : (N, 4) array or str
            The calculated values for setting edge or face_color
        """
        if n_points > 0:
            transformed_color = transform_color_with_defaults(
                num_entries=n_points,
                colors=color,
                elem_name=f"{attribute}_color",
                default="red",
            )
            init_colors = normalize_and_broadcast_colors(n_points, transformed_color)
        else:
            init_colors = np.empty((0, 4))
        return init_colors

    def _update_thumbnail(self):
        """Update thumbnail with current data"""
        colormapped = np.zeros(self._thumbnail_shape)
        colormapped[..., 3] = 1
        view_data = self._view_data
        if len(view_data) > 0:
            de = self._extent_data
            min_vals = [de[0, i] for i in self._dims_displayed]
            shape = np.ceil([de[1, i] - de[0, i] + 1 for i in self._dims_displayed]).astype(int)
            zoom_factor = np.divide(self._thumbnail_shape[:2], shape[-2:]).min()
            if len(view_data) > self._max_points_thumbnail:
                points = view_data[np.random.randint(0, len(view_data), self._max_points_thumbnail)]
            else:
                points = view_data
            coords = np.floor((points[:, -2:] - min_vals[-2:] + 0.5) * zoom_factor).astype(int)
            coords = np.clip(coords, 0, np.subtract(self._thumbnail_shape[:2], 1))
            colormapped[coords[:, 0], coords[:, 1]] = (1, 1, 1, 1)

        colormapped[..., 3] *= self.opacity
        self.thumbnail = colormapped

    def _set_view_slice(self):
        self.events.set_data()

    def _get_value(self, position):
        return position[1]

    @property
    def _extent_data(self) -> np.ndarray:
        if len(self.data) == 0:
            extrema = np.full((2, 2), np.nan)
        else:
            maxs = np.max(self.data, axis=0)
            mins = np.min(self.data, axis=0)
            extrema = np.vstack([mins, maxs])
        return extrema

    @property
    def data(self):
        """Return data"""
        return self._data

    @data.setter
    def data(self, value: np.ndarray):
        n = len(self._data)
        face_color = self.face_color
        edge_color = self.edge_color
        size = self.size
        edge_width = self.edge_width
        n_new = len(value)
        # fewer points, trim attributes
        if n > n_new:
            face_color = face_color[:n_new]
            edge_color = edge_color[:n_new]
            size = size[:n_new]
            edge_width = edge_width[:n_new]
        elif n < n_new:
            n_difference = n_new - n
            _new_face_color = face_color[-1] if len(face_color) > 0 else self._default_face_color
            face_color = np.concatenate([face_color, np.full((n_difference, 4), fill_value=_new_face_color)])
            _new_edge_color = edge_color[-1] if len(edge_color) > 0 else self._default_edge_color
            edge_color = np.concatenate([edge_color, np.full((n_difference, 4), fill_value=_new_edge_color)])
            _new_size = size[-1] if len(size) > 0 else self._default_size
            size = np.concatenate([size, np.full(n_difference, fill_value=_new_size)])
            _new_size = edge_width[-1] if len(edge_width) > 0 else self._default_edge_width
            edge_width = np.concatenate([edge_width, np.full(n_difference, fill_value=_new_size)])
        self._data = np.asarray(value)
        with self.events.blocker_all():
            self.edge_color = edge_color
            self.face_color = face_color
            self.size = size
            self.edge_width = edge_width
        self._emit_new_data()

    @property
    def x(self):
        """Return x-axis array."""
        return self.data[:, 0]

    @x.setter
    def x(self, value):
        value = np.asarray(value)
        if self.data.shape[0] != value.shape[0]:
            raise ValueError("The shape of the `x-axis` array does not match the shape of the `data` array.")
        self.data[:, 0] = value
        self._emit_new_data()

    @property
    def y(self):
        """Return y-axis array."""
        return self.data[:, 1]

    @y.setter
    def y(self, value):
        value = np.asarray(value)
        if self.data.shape[0] != value.shape[0]:
            raise ValueError("The shape of the `x-axis` array does not match the shape of the `data` array.")
        self.data[:, 1] = value
        self._emit_new_data()

    @property
    def symbol(self) -> str:
        """str: symbol used for all point markers."""
        return str(self._symbol)

    @symbol.setter
    def symbol(self, symbol: ty.Union[str, Symbol]) -> None:
        if isinstance(symbol, str):
            # Convert the alias string to the deduplicated string
            if symbol in SYMBOL_ALIAS:
                symbol = SYMBOL_ALIAS[symbol]
            else:
                symbol = Symbol(symbol)
        self._symbol = symbol
        self.events.symbol()

    @property
    def size(self) -> ty.Union[int, float, np.ndarray, list]:
        """(N, 1) array: size of all N points in D dimensions."""
        return self._size

    @size.setter
    def size(self, size: ty.Union[int, float, np.ndarray, list]) -> None:
        self._size = np.broadcast_to(size, self.data.shape[0]).copy()
        if len(self._size) > 0:
            self._default_size = self._size[-1]
        self.refresh()

    @property
    def scaling(self):
        """Scaling of the markers"""
        return self._scaling

    @scaling.setter
    def scaling(self, value):
        self._scaling = value
        self.events.scaling()

    @property
    def edge_width(self) -> np.ndarray:
        """float: width used for all point markers."""
        return self._edge_width

    @edge_width.setter
    def edge_width(self, edge_width: ty.Union[float, np.ndarray]) -> None:
        edge_width = np.broadcast_to(edge_width, self.data.shape[0]).copy()
        if self.edge_width_is_relative and np.any((edge_width > 1) | (edge_width < 0)):
            raise ValueError(
                "edge_width must be between 0 and 1 if edge_width_is_relative is enabled",
            )
        self._edge_width = edge_width
        if len(self._edge_width) > 0:
            self._default_edge_width = self._edge_width[-1]
        self.events.edge_width()

    @property
    def edge_width_is_relative(self) -> bool:
        """bool: treat edge_width as a fraction of point size."""
        return self._edge_width_is_relative

    @edge_width_is_relative.setter
    def edge_width_is_relative(self, edge_width_is_relative: bool) -> None:
        if edge_width_is_relative and np.any((self.edge_width > 1) | (self.edge_width < 0)):
            raise ValueError(
                "edge_width_is_relative can only be enabled if edge_width is between 0 and 1",
            )
        self._edge_width_is_relative = edge_width_is_relative
        self.events.edge_width_is_relative()

    @property
    def edge_color(self) -> np.ndarray:
        """(N x 4) np.ndarray: Array of RGBA edge colors for each point"""
        return self._edge_color

    @edge_color.setter
    def edge_color(self, edge_color):
        self._edge_color = self._initialize_color(edge_color, "edge", len(self._data))
        if len(self._edge_color) > 0:
            self._default_edge_color = self._edge_color[-1]
        self.events.edge_color()

    @property
    def face_color(self) -> np.ndarray:
        """(N x 4) np.ndarray: Array of RGBA face colors for each point"""
        return self._face_color

    @face_color.setter
    def face_color(self, face_color):
        self._face_color = self._initialize_color(face_color, "face", len(self._data))
        if len(self._face_color) > 0:
            self._default_face_color = self._face_color[-1]
        self.events.face_color()

    @property
    def properties(self) -> ty.Dict[str, np.ndarray]:
        """dict {str: np.ndarray (N,)}, DataFrame: Annotations for each point"""
        return self._properties

    @properties.setter
    def properties(self, properties: ty.Dict[str, np.ndarray]):
        if not isinstance(properties, dict):
            properties, _ = dataframe_to_properties(properties)
        self._properties = self._validate_properties(properties)

        if self.text.values is not None:
            self.refresh_text()
        self.events.properties()

    def _validate_properties(self, properties: ty.Dict[str, np.ndarray]) -> ty.Dict[str, np.ndarray]:
        """Validates the type and size of the properties"""
        for k, v in properties.items():
            if len(v) != len(self.data):
                raise ValueError("the number of properties must equal the number of points")
            # ensure the property values are a numpy array
            if type(v) != np.ndarray:
                properties[k] = np.asarray(v)
        return properties

    @property
    def text(self) -> TextManager:
        """TextManager: the TextManager object containing containing the text properties"""
        return self._text

    @text.setter
    def text(self, text):
        self._text._set_text(text, n_text=len(self.data), properties=self.properties)

    def refresh_text(self):
        """Refresh the text values.

        This is generally used if the properties were updated without changing the data
        """
        self.text.refresh_text(self.properties)

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
    def _view_text(self) -> np.ndarray:
        """Get the values of the text elements in view

        Returns
        -------
        text : (N x 1) np.ndarray
            Array of text strings for the N text elements in view
        """
        return self.text.view_text(np.arange(len(self.data)))

    @property
    def _view_text_coords(self) -> ty.Tuple[np.ndarray, str, str]:
        """Get the coordinates of the text elements in view

        Returns
        -------
        text_coords : (N x D) np.ndarray
            Array of coordinates for the N text elements in view
        """
        return self.text.compute_text_coords(self._view_data, 2)

    @property
    def label(self):
        """Get label"""
        return self._label

    @label.setter
    def label(self, value):
        self._label = value
        self.events.label()

    def _get_state(self):
        state = self._get_base_state()
        state.update(
            {
                "data": self.data,
                "symbol": self.symbol,
                "face_color": self.face_color,
                "edge_width": self.edge_width,
                "edge_color": self.edge_color,
                "scaling": self.scaling,
                "size": self.size,
                "label": self.label,
            }
        )
        return state

    def _get_mask_from_path(self, vertices):
        """Return data contained for specified vertices. Only certain layers implement this."""
        from matplotlib.path import Path

        path = Path(vertices)
        indices = path.contains_points(self.data)
        return indices
