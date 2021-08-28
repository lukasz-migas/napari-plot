"""Line layer"""
import numpy as np
from napari.layers import Layer
from napari.utils.events import Event

from ._centroids_constants import Method, Orientation
from ._centroids_utils import preprocess_centroids


class Centroids(Layer):
    """Centroids layer"""

    def __init__(
        self,
        data,
        *,
        orientation="vertical",
        color=(1.0, 1.0, 1.0, 1.0),
        width=2,
        method="gl",
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
            data = np.empty((0, 3))
        else:
            data = np.asarray(data)
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
        self._data = preprocess_centroids(data)
        self._color = color
        self._width = width
        self._method = Method(method)
        self._orientation = Orientation(orientation)

        self.events.add(color=Event, width=Event, method=Event, highlight=Event)
        self.visible = visible

    @property
    def orientation(self):
        """Orientation of the centroids layer."""
        return self._orientation

    @orientation.setter
    def orientation(self, value):
        self._orientation = Orientation(value)
        self.events.set_data()

    def _get_ndim(self):
        """Determine number of dimensions of the layer"""
        return 2

    def _get_state(self):
        """Get dictionary of layer state"""
        state = self._get_base_state()
        state.update(
            {
                "data": self.data,
                "color": self.color,
                "width": self.width,
                "method": self.method,
            }
        )
        return state

    def _update_thumbnail(self):
        """Update thumbnail with current data"""
        h = self._thumbnail_shape[0]
        colormapped = np.zeros(self._thumbnail_shape)
        colormapped[..., 3] = 1
        colormapped[h - 2 : h + 2, :] = 1  # horizontal strip
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
    def data(self):
        """Return data"""
        return self._data

    @data.setter
    def data(self, value: np.ndarray):
        self._data = value

        self._update_dims()
        self.events.data(value=self.data)
        self._set_editable()

    @property
    def color(self):
        """Get color"""
        return self._color

    @color.setter
    def color(self, value):
        self._color = value
        self.events.color()

    @property
    def width(self):
        """Get width"""
        return self._width

    @width.setter
    def width(self, value):
        self._width = value
        self.events.width()

    @property
    def method(self):
        """Get method"""
        return self._method

    @method.setter
    def method(self, value):
        self._method = value
        self.events.method()

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
