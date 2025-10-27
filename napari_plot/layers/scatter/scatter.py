"""Scatter layer."""

from __future__ import annotations

import typing as ty

import numpy as np
from napari.layers import Points
from napari.layers.base import Layer, no_op
from napari.layers.base._base_constants import Mode
from napari.layers.base._base_mouse_bindings import highlight_box_handles, transform_with_box
from napari.layers.points._points_utils import fix_data_points
from napari.utils.events import Event
from napari.utils.migrations import add_deprecated_property, rename_argument

from napari_plot.layers.base import LayerMixin


class Scatter(Points, LayerMixin):
    """Scatter layer based on napari Points layer.

    Parameters
    ----------
    data : array (N, 2)
        Coordinates for N points in 2 dimensions. Data is expected as [y, x]
    features : dict[str, array-like] or DataFrame
        Features table where each row corresponds to a point and each column
        is a feature.
    properties : dict {str: array (N,)}, DataFrame
        Properties for each point. Each property should be an array of length N, where N is the number of points.
    property_choices : dict {str: array (N,)}
        possible values for each property.
    text : str, dict
        Text to be displayed with the points. If text is set to a key in properties, the value of that property will
        be displayed. Multiple properties can be composed using f-string-like syntax
        (e.g., '{property_1}, {float_property:.2f}). A dictionary can be provided with keyword arguments to set the text
        values and display properties. See TextManager.__init__() for the valid keyword arguments.
        For example usage, see /napari/examples/add_points_with_text.py.
    symbol : str
        Symbol to be used for the point markers. Must be one of the following: arrow, clobber, cross, diamond, disc,
        hbar, ring, square, star, tailed_arrow, triangle_down, triangle_up, vbar, x.
    size : float, array
        Size of the point marker in data pixels. If given as a scalar, all points are made the same size. If given as an
        array, size must be the same or broadcastable to the same shape as the data.
    border_width : float, array
        Width of the symbol edge in pixels.
    border_width_is_relative : bool
        If enabled, border_width is interpreted as a fraction of the point size.
    border_color : str, array-like, dict
        Color of the point marker border. Numeric color values should be RGB(A).
    border_color_cycle : np.ndarray, list
        Cycle of colors (provided as string name, RGB, or RGBA) to map to border_color if a
        categorical attribute is used color the vectors.
    border_colormap : str, napari.utils.Colormap
        Colormap to set border_color if a continuous attribute is used to set face_color.
    border_contrast_limits : None, (float, float)
        clims for mapping the property to a color map. These are the min and max value of the specified property that
        are mapped to 0 and 1, respectively. The default value is None. If set the none, the clims will be set to
        (property.min(), property.max())
    face_color : str, array-like, dict
        Color of the point marker body. Numeric color values should be RGB(A).
    face_color_cycle : np.ndarray, list
        Cycle of colors (provided as string name, RGB, or RGBA) to map to face_color if a categorical attribute is used
        color the vectors.
    face_colormap : str, napari.utils.Colormap
        Colormap to set face_color if a continuous attribute is used to set face_color.
    face_contrast_limits : None, (float, float)
        clims for mapping the property to a color map. These are the min and max value of the specified property that
        are mapped to 0 and 1, respectively. The default value is None. If set the none, the clims will be set to
        (property.min(), property.max())
    out_of_slice_display : bool
        If True, renders points not just in central plane but also slightly out of slice according to specified point
        marker size.
    name : str
        Name of the layer.
    metadata : dict
        Layer metadata.
    scale : tuple of float
        Scale factors for the layer.
    translate : tuple of float
        Translation values for the layer.
    rotate : float, 3-tuple of float, or n-D array.
        If a float convert into a 2D rotation matrix using that value as an angle. If 3-tuple convert into a 3D rotation
        matrix, using a yaw, pitch, roll convention. Otherwise assume an nD rotation. Angles are assumed to be in
        degrees. They can be converted from radians with np.degrees if needed.
    shear : 1-D array or n-D array
        Either a vector of upper triangular values, or an nD shear matrix with ones along the main diagonal.
    affine : n-D array or napari.utils.transforms.Affine
        (N+1, N+1) affine transformation matrix in homogeneous coordinates. The first (N, N) entries correspond to a
        linear transform and the final column is a length N translation vector and a 1 or a napari
        `Affine` transform object. Applied as an extra transform on top of the
        provided scale, rotate, and shear values.
    opacity : float
        Opacity of the layer visual, between 0.0 and 1.0.
    blending : str
        One of a list of preset blending modes that determines how RGB and alpha values of the layer visual get mixed.
        Allowed values are {'opaque', 'translucent', and 'additive'}.
    visible : bool
        Whether the layer visual is currently being displayed.
    cache : bool
        Whether slices of out-of-core datasets should be cached upon retrieval. Currently, this only applies to dask
        arrays.
    shading : str, Shading
        Render lighting and shading on points. Options are:

        * 'none'
          No shading is added to the points.
        * 'spherical'
          Shading and depth buffer are changed to give a 3D spherical look to the points
    antialiasing: float
        Amount of antialiasing in canvas pixels.
    canvas_size_limits : tuple of float
        Lower and upper limits for the size of points in canvas pixels.
    shown : 1-D array of bool
        Whether to show each point.
    scaling : bool
        Whether to scale the points with the zoom level.
    label : str
        Label to be used with legend - currently does not do anything.
    """

    _modeclass = Mode
    _drag_modes: ty.ClassVar[dict[Mode, ty.Callable[[Scatter, Event], ty.Any]]] = {
        Mode.PAN_ZOOM: no_op,
        Mode.TRANSFORM: transform_with_box,
    }

    _move_modes: ty.ClassVar[dict[Mode, ty.Callable[[Scatter, Event], ty.Any]]] = {
        Mode.PAN_ZOOM: no_op,
        Mode.TRANSFORM: highlight_box_handles,
    }
    _cursor_modes: ty.ClassVar[dict[Mode, str]] = {
        Mode.PAN_ZOOM: "standard",
        Mode.TRANSFORM: "standard",
    }

    _default_face_color = np.array((1.0, 1.0, 1.0, 1.0), dtype=np.float32)
    _default_border_color = np.array((1.0, 1.0, 1.0, 1.0), dtype=np.float32)
    _default_border_width = 1
    _default_size = 1
    _default_rel_size = 0.1

    @rename_argument("edge_width", "border_width", since_version="0.2.0", version="0.3.0")
    @rename_argument(
        "edge_width_is_relative",
        "border_width_is_relative",
        since_version="0.5.0",
        version="0.6.0",
    )
    @rename_argument("edge_color", "border_color", since_version="0.2.0", version="0.3.0")
    @rename_argument("edge_color_cycle", "border_color_cycle", since_version="0.2.0", version="0.3.0")
    @rename_argument("edge_colormap", "border_colormap", since_version="0.2.0", version="0.3.0")
    @rename_argument(
        "edge_contrast_limits",
        "border_contrast_limits",
        since_version="0.2.0",
        version="0.3.0",
    )
    def __init__(
        self,
        data=None,
        *,
        features=None,
        properties=None,
        text=None,
        symbol="o",
        size=10,
        border_width=0.05,
        border_width_is_relative=True,
        border_color="dimgray",
        border_color_cycle=None,
        border_colormap="viridis",
        border_contrast_limits=None,
        face_color="white",
        face_color_cycle=None,
        face_colormap="viridis",
        face_contrast_limits=None,
        out_of_slice_display=False,
        name=None,
        metadata=None,
        scale=None,
        translate=None,
        rotate=None,
        shear=None,
        affine=None,
        opacity=1,
        blending="translucent",
        visible=True,
        cache=True,
        property_choices=None,
        experimental_clipping_planes=None,
        shading="none",
        shown=True,
        scaling=True,
        canvas_size_limits=(2, 10000),
        antialiasing=1,
    ):
        data, ndim = fix_data_points(data, 2)
        if ndim > 2:
            raise ValueError("Scatter layer only supports 2D data.")
        Points.__init__(
            self,
            data=data,
            ndim=ndim,
            features=features,
            properties=properties,
            text=text,
            symbol=symbol,
            size=size,
            border_width=border_width,
            border_width_is_relative=border_width_is_relative,
            border_color=border_color,
            border_color_cycle=border_color_cycle,
            border_colormap=border_colormap,
            border_contrast_limits=border_contrast_limits,
            face_color=face_color,
            face_color_cycle=face_color_cycle,
            face_colormap=face_colormap,
            face_contrast_limits=face_contrast_limits,
            out_of_slice_display=out_of_slice_display,
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
            cache=cache,
            property_choices=property_choices,
            experimental_clipping_planes=experimental_clipping_planes,
            shading=shading,
            shown=shown,
            canvas_size_limits=canvas_size_limits,
            antialiasing=antialiasing,
        )
        self._mode = Mode.PAN_ZOOM
        self.events.add(scaling=Event)
        self.scaling = scaling

    def _mode_setter_helper(self, mode):
        mode = Layer._mode_setter_helper(self, mode)
        if mode == self._mode:
            return mode
        self._set_highlight()
        return mode

    @classmethod
    def _add_deprecated_properties(cls) -> None:
        """Adds deprecated properties to class."""
        deprecated_properties = [
            "edge_width",
            "edge_width_is_relative",
            "current_edge_width",
            "edge_color",
            "edge_color_cycle",
            "edge_colormap",
            "edge_contrast_limits",
            "current_edge_color",
            "edge_color_mode",
        ]
        for old_property in deprecated_properties:
            new_property = old_property.replace("edge", "border")
            add_deprecated_property(
                cls,
                old_property,
                new_property,
                since_version="0.2.0",
                version="0.3.0",
            )

    @property
    def scaling(self):
        """Scaling of the markers"""
        return self._scaling

    @scaling.setter
    def scaling(self, value):
        self._scaling = value
        self.events.scaling()

    @property
    def data(self) -> np.ndarray:
        """(N, D) array: coordinates for N points in D dimensions."""
        return self._data

    @data.setter
    def data(self, data):
        data, _ = fix_data_points(data, self.ndim)
        if data.ndim > 2:
            raise ValueError("Scatter layer only supports 2D data.")
        super(Scatter, self.__class__).data.fset(self, data)

    @property
    def x(self):
        """Return x-axis array."""
        return self.data[:, 1]

    @x.setter
    def x(self, value):
        value = np.asarray(value)
        if value.ndim > 1:
            raise ValueError("The `x-axis` array must be 1D.")
        if self.data.shape[0] != value.shape[0]:
            raise ValueError("The shape of the `x-axis` array does not match the shape of the `data` array.")
        self.data[:, 1] = value
        self._emit_new_data()

    @property
    def y(self):
        """Return y-axis array."""
        return self.data[:, 0]

    @y.setter
    def y(self, value):
        value = np.asarray(value)
        if value.ndim > 1:
            raise ValueError("The `y-axis` array must be 1D.")
        if self.data.shape[0] != value.shape[0]:
            raise ValueError("The shape of the `x-axis` array does not match the shape of the `data` array.")
        self.data[:, 0] = value
        self._emit_new_data()

    def _get_mask_from_path(self, vertices, as_indices: bool = False) -> np.ndarray:
        """Return data contained for specified vertices. Only certain layers implement this."""
        from matplotlib.path import Path

        path = Path(vertices)
        mask = path.contains_points(self.data)
        if as_indices:
            return np.nonzero(mask)[0]
        return mask
