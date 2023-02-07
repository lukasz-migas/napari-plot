"""Scatter layer."""
import numpy as np
from napari.layers import Points
from napari.layers.points._points_utils import fix_data_points
from napari.utils.events import Event

from napari_plot.layers.base import LayerMixin


class Scatter(Points, LayerMixin):
    """Scatter layer base on Points."""

    _default_face_color = np.array((1.0, 1.0, 1.0, 1.0), dtype=np.float32)
    _default_edge_color = np.array((1.0, 1.0, 1.0, 1.0), dtype=np.float32)
    _default_edge_width = 1
    _default_size = 1
    _default_rel_size = 0.1

    def __init__(
        self,
        data=None,
        *,
        ndim=None,
        features=None,
        properties=None,
        text=None,
        symbol="o",
        size=10,
        edge_width=0.05,
        edge_width_is_relative=True,
        edge_color="dimgray",
        edge_color_cycle=None,
        edge_colormap="viridis",
        edge_contrast_limits=None,
        face_color="white",
        face_color_cycle=None,
        face_colormap="viridis",
        face_contrast_limits=None,
        out_of_slice_display=False,
        n_dimensional=None,
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
        label="",
    ):
        if data is None:
            data = np.empty((0, 2))
        else:
            data = np.asarray(data)
        Points.__init__(
            self,
            data=data,
            ndim=ndim,
            features=features,
            properties=properties,
            text=text,
            symbol=symbol,
            size=size,
            edge_width=edge_width,
            edge_width_is_relative=edge_width_is_relative,
            edge_color=edge_color,
            edge_color_cycle=edge_color_cycle,
            edge_colormap=edge_colormap,
            edge_contrast_limits=edge_contrast_limits,
            face_color=face_color,
            face_color_cycle=face_color_cycle,
            face_colormap=face_colormap,
            face_contrast_limits=face_contrast_limits,
            out_of_slice_display=out_of_slice_display,
            n_dimensional=n_dimensional,
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
            # canvas_size_limits=canvas_size_limits,
            # antialiasing=antialiasing,
        )
        # LayerMixin.__init__(self, label=label)
        self._label = label
        self.events.add(scaling=Event, label=Event)
        with self.events.blocker_all():
            self.scaling = scaling

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
            raise ValueError("Data array should be 2D")
        # data = data[:, ::-1]
        super(Scatter, self.__class__).data.fset(self, data)

    @property
    def x(self):
        """Return x-axis array."""
        return self.data[:, 1]

    @x.setter
    def x(self, value):
        value = np.asarray(value)
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
        if self.data.shape[0] != value.shape[0]:
            raise ValueError("The shape of the `x-axis` array does not match the shape of the `data` array.")
        self.data[:, 0] = value
        self._emit_new_data()

    @property
    def _view_text_color(self) -> np.ndarray:
        """Get the colors of the text elements at the given indices."""
        self.text.color._apply(self.features)
        return self.text._view_color(self._indices_view)

    #
    # @property
    # def _view_symbol(self) -> np.ndarray:
    #     """Get the symbols of the points in view
    #
    #     Returns
    #     -------
    #     symbol : (N,) np.ndarray
    #         Array of symbol strings for the N points in view
    #     """
    #     return self.symbol[self._indices_view]

    def _get_mask_from_path(self, vertices):
        """Return data contained for specified vertices. Only certain layers implement this."""
        from matplotlib.path import Path

        path = Path(vertices)
        indices = path.contains_points(self.data)
        return indices
