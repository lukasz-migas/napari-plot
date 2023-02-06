"""Scatter points layer"""
import numbers
import typing as ty
import warnings
from copy import copy, deepcopy
from itertools import cycle

import numpy as np
from napari.layers.points._points_constants import ColorMode, Symbol
from napari.layers.points._points_utils import fix_data_points
from napari.layers.utils.color_manager import ColorManager
from napari.layers.utils.color_transformations import normalize_and_broadcast_colors, transform_color_with_defaults
from napari.layers.utils.text_manager import TextManager
from napari.utils import Colormap
from napari.utils.colormaps import ValidColormapArg
from napari.utils.colormaps.colormap_utils import ColorType
from napari.utils.colormaps.standardize_color import hex_to_name, rgb_to_hex
from napari.utils.events import Event
from napari.layers.utils.layer_utils import _FeatureTable

from ..base import BaseLayer
from ._utilities import coerce_symbols

if ty.TYPE_CHECKING:
    import pandas as pd


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
        data=None,
        *,
        # napari-plot parameters
        symbol="o",
        text=None,
        edge_width=0.1,
        edge_width_is_relative=True,
        edge_color="dimgray",
        edge_color_cycle=None,
        edge_colormap="viridis",
        edge_contrast_limits=None,
        face_color="white",
        face_color_cycle=None,
        face_colormap="viridis",
        face_contrast_limits=None,
        size=1,
        scaling=True,
        features=None,
        properties=None,
        label="",
        property_choices=None,
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
            features=Event,
            feature_defaults=Event,
            highlight=Event,
            current_face_color=Event,
            current_edge_color=Event,
            current_properties=Event,
        )

        # add data
        self._data = data
        self._edge_width_is_relative = False
        # The following point properties are for the new points that will
        # be added. For any given property, if a list is passed to the
        # constructor so each point gets its own value then the default
        # value is used when adding new points
        self._current_size = np.asarray(size) if np.isscalar(size) else 10
        self._current_edge_width = np.asarray(edge_width) if np.isscalar(edge_width) else 0.1
        self.current_symbol = np.asarray(symbol) if np.isscalar(symbol) else "o"

        # Features table
        self._feature_table = _FeatureTable.from_layer(
            features=features,
            properties=properties,
            property_choices=property_choices,
            num_data=len(self.data),
        )

        color_properties = self.properties if self._data.size > 0 else self.property_choices
        self._edge = ColorManager._from_layer_kwargs(
            n_colors=len(data),
            colors=edge_color,
            continuous_colormap=edge_colormap,
            contrast_limits=edge_contrast_limits,
            categorical_colormap=edge_color_cycle,
            properties=color_properties,
        )
        self._face = ColorManager._from_layer_kwargs(
            n_colors=len(data),
            colors=face_color,
            continuous_colormap=face_colormap,
            contrast_limits=face_contrast_limits,
            categorical_colormap=face_color_cycle,
            properties=color_properties,
        )

        # make the text
        if text is None or isinstance(text, (list, np.ndarray, str)):
            self._text = TextManager(text=text, n_text=len(data), properties=self.properties)
        elif isinstance(text, dict):
            copied_text = deepcopy(text)
            copied_text["properties"] = self.properties
            copied_text["n_text"] = len(data)
            self._text = TextManager(**copied_text)
        else:
            raise TypeError("text should be a string, array, or dict")
        with self.events.blocker_all():
            self.scaling = scaling
            self.edge_width = edge_width
            self.size = size
            self.symbol = symbol
            self.edge_width = edge_width
            self.edge_width_is_relative = edge_width_is_relative
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
    def data(self, data: np.ndarray):
        data, _ = fix_data_points(data, self.ndim)
        n = len(self._data)
        self._data = data

        with self.events.blocker_all(), self._edge.events.blocker_all(), self._face.events.blocker_all():
            self._feature_table.resize(len(data))
            self.text.apply(self.features)
        if len(data) < n:
            # If there are now fewer points, remove the size and colors of the
            # extra ones
            if len(self._edge.colors) > len(data):
                self._edge._remove(np.arange(len(data), len(self._edge.colors)))
            if len(self._face.colors) > len(data):
                self._face._remove(np.arange(len(data), len(self._face.colors)))
            # self._shown = self._shown[: len(data)]
            self._size = self._size[: len(data)]
            self._edge_width = self._edge_width[: len(data)]
            self._symbol = self._symbol[: len(data)]
        elif len(data) > n:
            # If there are now more points, add the size and colors of the new ones
            adding = len(data) - n
            if len(self._size) > 0:
                new_size = copy(self._size[-1])
                for i in [0, 1]:
                    new_size[i] = self.current_size
            else:
                # Add the default size, with a value for each dimension
                new_size = np.repeat(self.current_size, self._size.shape[0])
            size = np.repeat([new_size], adding, axis=0)

            if len(self._edge_width) > 0:
                new_edge_width = copy(self._edge_width[-1])
            else:
                new_edge_width = self.current_edge_width
            edge_width = np.repeat([new_edge_width], adding, axis=0)

            if len(self._symbol) > 0:
                new_symbol = copy(self._symbol[-1])
            else:
                new_symbol = self.current_symbol
            symbol = np.repeat([new_symbol], adding, axis=0)

            # add new colors
            self._edge._add(n_colors=adding)
            self._face._add(n_colors=adding)

            self.size = np.concatenate((self._size, size), axis=0)
            self.edge_width = np.concatenate((self._edge_width, edge_width), axis=0)
            self.symbol = np.concatenate((self._symbol, symbol), axis=0)
        self._emit_new_data()

    @property
    def current_size(self) -> ty.Union[int, float]:
        """float: size of marker for the next added point."""
        return self._current_size

    @current_size.setter
    def current_size(self, size: ty.Union[None, float]) -> None:
        if (isinstance(size, numbers.Number) and size < 0) or (isinstance(size, list) and min(size) < 0):
            warnings.warn(
                f"current_size value must be positive, value will be left at {self.current_size}.",
                category=RuntimeWarning,
            )
            size = self.current_size
        self._current_size = size
        # if self._update_properties and len(self.selected_data) > 0:
        #     for i in self.selected_data:
        #         self.size[i, :] = (self.size[i, :] > 0) * size
        #     self.refresh()
        #     self.events.size()

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
    def symbol(self) -> np.ndarray:
        """str: symbol used for all point markers."""
        return self._symbol

    @symbol.setter
    def symbol(self, symbol: ty.Union[str, np.ndarray, list]) -> None:
        symbol = np.broadcast_to(symbol, self.data.shape[0])
        self._symbol = coerce_symbols(symbol)
        self.events.symbol()
        self.events.highlight()

    @property
    def size(self) -> np.ndarray:
        """(N, D) array: size of all N points in D dimensions."""
        return self._size

    @size.setter
    def size(self, size: ty.Union[int, float, np.ndarray, list]) -> None:
        try:
            self._size = np.broadcast_to(size, self.data.shape).copy()
        except Exception:
            try:
                self._size = np.broadcast_to(size, self.data.shape[::-1]).T.copy()
            except Exception:
                raise ValueError("Size is not compatible for broadcasting")
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
    def current_edge_width(self) -> ty.Union[int, float]:
        """float: edge_width of marker for the next added point."""
        return self._current_edge_width

    @current_edge_width.setter
    def current_edge_width(self, edge_width: ty.Union[None, float]) -> None:
        self._current_edge_width = edge_width
        if self._update_properties and len(self.selected_data) > 0:
            for i in self.selected_data:
                self.edge_width[i] = (self.edge_width[i] > 0) * edge_width
            self.refresh()
            self.events.edge_width()

    @property
    def edge_color(self) -> np.ndarray:
        """(N x 4) np.ndarray: Array of RGBA edge colors for each point"""
        return self._edge.colors

    @edge_color.setter
    def edge_color(self, edge_color):
        self._edge._set_color(
            color=edge_color,
            n_colors=len(self.data),
            properties=self.properties,
            current_properties=self.current_properties,
        )
        self.events.edge_color()

    @property
    def edge_color_cycle(self) -> np.ndarray:
        """Union[list, np.ndarray] :  Color cycle for edge_color.
        Can be a list of colors defined by name, RGB or RGBA
        """
        return self._edge.categorical_colormap.fallback_color.values

    @edge_color_cycle.setter
    def edge_color_cycle(self, edge_color_cycle: ty.Union[list, np.ndarray]):
        self._edge.categorical_colormap = edge_color_cycle

    @property
    def edge_colormap(self) -> Colormap:
        """Return the colormap to be applied to a property to get the edge color.

        Returns
        -------
        colormap : napari.utils.Colormap
            The Colormap object.
        """
        return self._edge.continuous_colormap

    @edge_colormap.setter
    def edge_colormap(self, colormap: ValidColormapArg):
        self._edge.continuous_colormap = colormap

    @property
    def edge_contrast_limits(self) -> ty.Tuple[float, float]:
        """None, (float, float): contrast limits for mapping
        the edge_color colormap property to 0 and 1
        """
        return self._edge.contrast_limits

    @edge_contrast_limits.setter
    def edge_contrast_limits(self, contrast_limits: ty.Union[None, ty.Tuple[float, float]]):
        self._edge.contrast_limits = contrast_limits

    @property
    def current_edge_color(self) -> str:
        """str: Edge color of marker for the next added point or the selected point(s)."""
        hex_ = rgb_to_hex(self._edge.current_color)[0]
        return hex_to_name.get(hex_, hex_)

    @current_edge_color.setter
    def current_edge_color(self, edge_color: ColorType) -> None:
        if self._update_properties and len(self.selected_data) > 0:
            update_indices = list(self.selected_data)
        else:
            update_indices = []
        self._edge._update_current_color(edge_color, update_indices=update_indices)
        self.events.current_edge_color()

    @property
    def edge_color_mode(self) -> str:
        """str: Edge color setting mode

        DIRECT (default mode) allows each point to be set arbitrarily

        CYCLE allows the color to be set via a color cycle over an attribute

        COLORMAP allows color to be set via a color map over an attribute
        """
        return self._edge.color_mode

    @edge_color_mode.setter
    def edge_color_mode(self, edge_color_mode: ty.Union[str, ColorMode]):
        self._set_color_mode(edge_color_mode, "edge")

    @property
    def face_color(self) -> np.ndarray:
        """(N x 4) np.ndarray: Array of RGBA face colors for each point"""
        return self._face.colors

    @face_color.setter
    def face_color(self, face_color):
        self._face._set_color(
            color=face_color,
            n_colors=len(self.data),
            properties=self.properties,
            current_properties=self.current_properties,
        )
        self.events.face_color()

    @property
    def face_color_cycle(self) -> np.ndarray:
        """Union[np.ndarray, cycle]:  Color cycle for face_color
        Can be a list of colors defined by name, RGB or RGBA
        """
        return self._face.categorical_colormap.fallback_color.values

    @face_color_cycle.setter
    def face_color_cycle(self, face_color_cycle: ty.Union[np.ndarray, cycle]):
        self._face.categorical_colormap = face_color_cycle

    @property
    def face_colormap(self) -> Colormap:
        """Return the colormap to be applied to a property to get the face color.

        Returns
        -------
        colormap : napari.utils.Colormap
            The Colormap object.
        """
        return self._face.continuous_colormap

    @face_colormap.setter
    def face_colormap(self, colormap: ValidColormapArg):
        self._face.continuous_colormap = colormap

    @property
    def face_contrast_limits(self) -> ty.Union[None, ty.Tuple[float, float]]:
        """None, (float, float) : clims for mapping the face_color
        colormap property to 0 and 1
        """
        return self._face.contrast_limits

    @face_contrast_limits.setter
    def face_contrast_limits(self, contrast_limits: ty.Union[None, ty.Tuple[float, float]]):
        self._face.contrast_limits = contrast_limits

    @property
    def features(self):
        """Dataframe-like features table.

        It is an implementation detail that this is a `pandas.DataFrame`. In the future,
        we will target the currently-in-development Data API dataframe protocol [1].
        This will enable us to use alternate libraries such as xarray or cuDF for
        additional features without breaking existing usage of this.

        If you need to specifically rely on the pandas API, please coerce this to a
        `pandas.DataFrame` using `features_to_pandas_dataframe`.

        References
        ----------
        .. [1]: https://data-apis.org/dataframe-protocol/latest/API.html
        """
        return self._feature_table.values

    @features.setter
    def features(
        self,
        features: ty.Union[ty.Dict[str, np.ndarray], "pd.DataFrame"],
    ) -> None:
        self._feature_table.set_values(features, num_data=len(self.data))
        self._update_color_manager(self._face, self._feature_table, "face_color")
        self._update_color_manager(self._edge, self._feature_table, "edge_color")
        self.text.refresh(self.features)
        self.events.properties()
        self.events.features()

    @property
    def feature_defaults(self):
        """Dataframe-like with one row of feature default values.

        See `features` for more details on the type of this property.
        """
        return self._feature_table.defaults

    @property
    def property_choices(self) -> ty.Dict[str, np.ndarray]:
        """Property choices."""
        return self._feature_table.choices()

    @property
    def properties(self) -> ty.Dict[str, np.ndarray]:
        """dict {str: np.ndarray (N,)}, DataFrame: Annotations for each point"""
        return self._feature_table.properties()

    @property
    def current_properties(self) -> ty.Dict[str, np.ndarray]:
        """dict{str: np.ndarray(1,)}: properties for the next added point."""
        return self._feature_table.currents()

    @current_properties.setter
    def current_properties(self, current_properties):
        update_indices = None
        if self._update_properties and len(self.selected_data) > 0:
            update_indices = list(self.selected_data)
        self._feature_table.set_currents(current_properties, update_indices=update_indices)
        current_properties = self.current_properties
        self._edge._update_current_properties(current_properties)
        self._face._update_current_properties(current_properties)
        self.events.current_properties()
        self.events.feature_defaults()
        if update_indices is not None:
            self.events.properties()
            self.events.features()

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
        self._text._update_from_layer(text=text, features=self.features)

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
