"""Line layer"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import Event
from numpy.typing import ArrayLike

from napari_plot.layers._selection import points_in_polygon
from napari_plot.layers._thumbnail import LINE
from napari_plot.layers.base import _SelectableLayer
from napari_plot.layers.line._line_constants import Method


class Line(_SelectableLayer):
    """Line layer

    Parameters
    ----------
    data : array (N, 2)
        Coordinates for N points in 2 dimensions.
    color : str, array-like
        If string can be any color name recognized by vispy or hex value if starting with `#`. If array-like must
        be 1-dimensional array with 3 or 4 elements.
    width : float
        Width of the line in pixel units.
    method : str or Method
        Rendering method. Either `gl` or `agg`.
    dashes : sequence of float, optional
        Alternating visible and hidden lengths in multiples of line width.
        Dashed lines use VisPy's antialiased rendering method.
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
        data: ArrayLike | None,
        *,
        # napari-plot parameters
        color: Any = (1.0, 1.0, 1.0, 1.0),
        width: float = 2,
        method: str | Method = "gl",
        dashes: Sequence[float] | None = None,
        # napari parameters
        axis_labels=None,
        name=None,
        metadata=None,
        scale=None,
        translate=None,
        rotate=None,
        shear=None,
        affine=None,
        opacity=1.0,
        blending="translucent",
        experimental_clipping_planes=None,
        projection_mode="none",
        units=None,
        visible=True,
    ) -> None:
        # sanitize data
        data = np.empty((0, 2)) if data is None else np.asarray(data)

        super().__init__(
            data,
            axis_labels=axis_labels,
            name=name,
            metadata=metadata,
            scale=scale,
            translate=translate,
            rotate=rotate,
            shear=shear,
            affine=affine,
            opacity=opacity,
            blending=blending,
            experimental_clipping_planes=experimental_clipping_planes,
            projection_mode=projection_mode,
            units=units,
            visible=visible,
        )
        self.events.add(color=Event, width=Event, method=Event, dashes=Event, highlight=Event)

        self._data = data
        self._color = transform_color(color)[0]
        self._width = width
        self._method: Method | str = Method(method)
        self.dashes = dashes
        self.visible = visible

    def _get_state(self) -> dict[str, Any]:
        """Get dictionary of layer state"""
        state = self._get_base_state()
        state.update(
            {
                "data": self.data,
                "color": self.color,
                "width": self.width,
                "method": self.method,
                "dashes": self.dashes,
            }
        )
        return state

    def _update_thumbnail(self) -> None:
        self._set_thumbnail_glyph(LINE, self.color)

    @property
    def _view_data(self) -> np.ndarray:
        """Get the coords of the points in view

        Returns
        -------
        view_data : (N x D) np.ndarray
            Array of coordinates for the N points in view
        """
        return self.data

    def _selection_mask(self, vertices: np.ndarray) -> np.ndarray:
        """Select sample indices whose coordinates are inside the polygon."""
        return points_in_polygon(np.asarray(self.data)[:, ::-1], vertices)

    @property
    def data(self) -> np.ndarray:
        """Return data."""
        return self._data

    @data.setter
    def data(self, value: np.ndarray) -> None:
        self._data = value
        self._emit_new_data()

    @property
    def x(self) -> np.ndarray:
        """Return x-axis array."""
        return self.data[:, 0]

    @x.setter
    def x(self, value: ArrayLike) -> None:
        value = np.asarray(value)
        if self.data.shape[0] != value.shape[0]:
            raise ValueError("The shape of the `x-axis` array does not match the shape of the `data` array.")
        self.data[:, 0] = value
        self._emit_new_data()

    @property
    def y(self) -> np.ndarray:
        """Return y-axis array."""
        return self.data[:, 1]

    @y.setter
    def y(self, value: ArrayLike) -> None:
        value = np.asarray(value)
        if self.data.shape[0] != value.shape[0]:
            raise ValueError("The shape of the `x-axis` array does not match the shape of the `data` array.")
        self.data[:, 1] = value
        self._emit_new_data()

    @property
    def color(self) -> np.ndarray:
        """Get color."""
        return self._color

    @color.setter
    def color(self, value: Any) -> None:
        self._color = transform_color(value)[0]
        self.events.color()
        self._update_thumbnail()

    @property
    def width(self) -> float:
        """Get width"""
        return self._width

    @width.setter
    def width(self, value: float) -> None:
        self._width = value
        self.events.width()

    @property
    def method(self) -> Method | str:
        """Get method"""
        return self._method

    @method.setter
    def method(self, value: Method | str) -> None:
        self._method = value
        self.events.method()

    @property
    def dashes(self) -> tuple[float, ...] | None:
        """Return the dash pattern, or None for a solid line."""
        return self._dashes

    @dashes.setter
    def dashes(self, value: Sequence[float] | None) -> None:
        pattern = tuple(map(float, value)) if value is not None else ()
        if pattern and (len(pattern) % 2 or not np.isfinite(pattern).all() or min(pattern) <= 0):
            raise ValueError("A dash pattern needs positive, finite pairs of visible and hidden lengths.")
        self._dashes = pattern or None
        self.events.dashes()

    def _set_view_slice(self):
        self.events.set_data()

    def _get_value(self, position):
        """Value of the data at a position in data coordinates"""
        return position[1]

    @property
    def _extent_data(self) -> np.ndarray:
        if len(self.data) == 0:
            extrema = np.full((2, 2), np.nan)
        else:
            maxs = np.max(self.data, axis=0)[::-1]
            mins = np.min(self.data, axis=0)[::-1]
            extrema = np.vstack([mins, maxs])
        return extrema

    def _get_x_region_extent(self, x_min: float, x_max: float) -> None:
        """Return data extents in the (xmin, xmax, ymin, ymax) format."""
        from napari_plot.utils.utilities import find_nearest_index, get_min_max

        idx_min, idx_max = find_nearest_index(self.x, [x_min, x_max])
        return get_min_max(self.y[idx_min : idx_max + 1])
