"""Viewer model"""
# Third-party imports
import warnings
from typing import Optional, Tuple

import numpy as np
from napari.components import Dims
from napari.components.cursor import Cursor
from napari.components.text_overlay import TextOverlay
from napari.layers import Layer
from napari.utils._register import create_func as create_add_method
from napari.utils.events import Event, EventedModel, disconnect_events
from napari.utils.key_bindings import KeymapProvider
from napari.utils.mouse_bindings import MousemapProvider
from pydantic import Field, Extra

# Local imports
# from .viewer_model import ViewerModelBase
from .. import layers
from ._viewer_mouse_bindings import x_span
from .axis import Axis
from .camera import Camera
from .span import Span
from ..utils.utilities import find_nearest_index, get_min_max
from .gridlines import GridLines
from .layerlist import LayerList


def get_x_region_extent(
    x_min: float, x_max: float, layer: Layer
) -> Tuple[Optional[float], ...]:
    """Get extent for specified range"""
    if not layer.visible:
        return None, None
    if layer.ndim != 2:
        return None, None
    if isinstance(layer, (layers.Line, layers.Centroids)):
        idx_min, idx_max = find_nearest_index(layer.data[:, 0], [x_min, x_max])
        if idx_min == idx_max:
            idx_max += 1
            if idx_max > len(layer.data):
                return None, None
        try:
            return get_min_max(layer.data[idx_min:idx_max, 1])
        except ValueError:
            return None, None
    if isinstance(layer, layers.Scatter):
        idx_min, idx_max = find_nearest_index(layer.data[:, 1], [x_min, x_max])
        if idx_min == idx_max:
            idx_max += 1
            if idx_max > len(layer.data):
                return None, None
        try:
            return get_min_max(layer.data[idx_min:idx_max, 0])
        except ValueError:
            return None, None
    return None, None


def get_layers_x_region_extent(
    x_min: float, x_max: float, layerlist
) -> Tuple[Optional[float], ...]:
    """Get layer extents"""
    extents = []
    for layer in layerlist:
        y_min, y_max = get_x_region_extent(x_min, x_max, layer)
        if y_min is None:
            continue
        extents.extend([y_min, y_max])
    if extents:
        extents = np.asarray(extents)
        return get_min_max(extents)
    return None, None


def get_range_extent(
    full_min, full_max, range_min, range_max, min_val: float = None
) -> Tuple[float, float]:
    """Get tuple of specified range"""
    if range_min is None:
        range_min = full_min
    if range_max is None:
        range_max = full_max
    if min_val is None:
        min_val = range_min
    return get_min_max([range_min, range_max, min_val])


class ViewerModel(KeymapProvider, MousemapProvider, EventedModel):
    """Viewer containing the rendered scene, layers, and controlling elements
    including dimension sliders, and control bars for color limits.

    Parameters
    ----------
    title : string
        The title of the viewer window.
    ndisplay : {2, 3}
        Number of displayed dimensions.
    order : tuple of int
        Order in which dimensions are displayed where the last two or last
        three dimensions correspond to row x column or plane x row x column if
        ndisplay is 2.
    axis_labels : list of str
        Dimension names.
    """

    # Using allow_mutation=False means these attributes aren't settable and don't
    # have an event emitter associated with them
    dims: Dims = Field(default_factory=Dims, allow_mutation=False)
    cursor: Cursor = Field(default_factory=Cursor, allow_mutation=False)
    grid_lines: GridLines = Field(default_factory=GridLines, allow_mutation=False)
    layers: LayerList = Field(default_factory=LayerList, allow_mutation=False)
    camera: Camera = Field(default_factory=Camera, allow_mutation=False)
    axis: Axis = Field(default_factory=Axis, allow_mutation=False)
    text_overlay: TextOverlay = Field(default_factory=TextOverlay, allow_mutation=False)
    span: Span = Field(default_factory=Span, allow_mutation=False)

    help: str = ""
    status: str = "Ready"
    title: str = "napari_1d"
    theme: str = "dark"

    # 2-tuple indicating height and width
    _canvas_size: Tuple[int, int] = (400, 400)

    def __init__(self, title="napari_1d", ndisplay=2, order=(), axis_labels=()):
        # allow extra attributes during model initialization, useful for mixins
        self.__config__.extra = Extra.allow
        super().__init__(
            title=title,
            dims={
                "axis_labels": axis_labels,
                "ndisplay": ndisplay,
                "order": order,
            },
        )
        self.__config__.extra = Extra.ignore

        self.events.add(layers_change=Event, reset_view=Event, span=Event)

        # Connect events
        self.dims.events.ndisplay.connect(self._update_layers)
        self.dims.events.ndisplay.connect(self.reset_view)
        self.dims.events.order.connect(self._update_layers)
        self.dims.events.order.connect(self.reset_view)
        self.dims.events.current_step.connect(self._update_layers)
        self.cursor.events.position.connect(self._on_cursor_position_change)
        self.layers.events.inserted.connect(self._on_add_layer)
        self.layers.events.removed.connect(self._on_remove_layer)
        self.layers.events.reordered.connect(self._on_layers_change)
        self.layers.selection.events.active.connect(self._on_active_layer)
        self.layers.events.inserted.connect(self._on_update_extent)
        self.layers.events.removed.connect(self._on_update_extent)
        self.events.layers_change.connect(self._on_update_extent)

        # Add mouse callback
        self.mouse_drag_callbacks.append(x_span)

    def _get_rect_extent(self) -> Tuple[float, ...]:
        """Get data extent"""
        extent = self._sliced_extent_world
        ymin, ymax = get_min_max(extent[:, 0])
        xmin, xmax = get_min_max(extent[:, 1])
        ymax *= 1.05
        return xmin - 1, xmax + 1, ymin, ymax

    def _on_update_extent(self, _event=None):
        """Update data extent when there has been a change to the list of layers"""
        self.camera.extent = self._get_rect_extent()

    def clear_canvas(self):
        """Remove all layers from the canvas"""
        self.layers.remove_all()
        self.events.clear_canvas()

    @property
    def _sliced_extent_world(self) -> np.ndarray:
        """Extent of layers in world coordinates after slicing.

        D is either 2 or 3 depending on if the displayed data is 2D or 3D.

        Returns
        -------
        sliced_extent_world : array, shape (2, D)
        """
        if len(self.layers) == 0 and self.dims.ndim != 2:
            # If no data is present and dims model has not been reset to 0
            # than someone has passed more than two axis labels which are
            # being saved and so default values are used.
            return np.vstack([np.zeros(self.dims.ndim), np.repeat(512, self.dims.ndim)])
        else:
            return self.layers.extent.world[:, self.dims.displayed]

    def _get_y_range_extent_for_x(
        self,
        xmin: float,
        xmax: float,
        ymin: float = 0,
        y_multiplier: float = 1.05,
        auto_scale: bool = True,
    ):
        """Calculate range for specified x-axis range."""
        _, _, real_ymin, real_ymax = self._get_rect_extent()
        if auto_scale:
            ymin, ymax = get_range_extent(
                real_ymin,
                real_ymax,
                *get_layers_x_region_extent(xmin, xmax, self.layers),
                ymin
            )
        else:
            ymin, ymax = real_ymin, real_ymax
        return ymin, ymax * y_multiplier

    def reset_view(self, event=None):
        """Reset the camera view."""
        xmin, xmax, ymin, ymax = self._get_rect_extent()
        self.camera.rect = (xmin, xmax, ymin, ymax)
        self.camera.angles = (0, 0, 90)

    def set_x_view(
        self,
        xmin: float,
        xmax: float,
        ymin: float = 0,
        y_multiplier: float = 1.05,
        auto_scale: bool = True,
    ):
        """Set view on specified x-axis"""
        ymin, ymax = self._get_y_range_extent_for_x(
            xmin, xmax, ymin, y_multiplier=y_multiplier, auto_scale=auto_scale
        )
        self.camera.rect = (xmin, xmax, ymin, ymax)

    def reset_x_view(self, event=None):
        """Reset the camera view, but only in the y-axis dimension"""
        xmin, xmax, _, _ = self._get_rect_extent()
        _, _, ymin, ymax = self.camera.rect
        self.camera.rect = (xmin, xmax, ymin, ymax)
        self.camera.angles = (0, 0, 90)

    def set_y_view(self, ymin: float, ymax: float):
        """Set view on specified y-axis"""
        xmin, xmax, _, _ = self._get_rect_extent()
        self.camera.rect = (xmin, xmax, ymin, ymax)

    def reset_y_view(self, event=None):
        """Reset the camera view, but only in the y-axis dimension"""
        _, _, ymin, ymax = self._get_rect_extent()
        xmin, xmax, _, _ = self.camera.rect
        self.camera.rect = (xmin, xmax, ymin, ymax)
        self.camera.angles = (0, 0, 90)

    def _update_layers(self, event=None, layers=None):
        """Updates the contained layers.

        Parameters
        ----------
        layers : list of napari.layers.Layer, optional
            List of layers to update. If none provided updates all.
        """
        layers = layers or self.layers
        for layer in layers:
            layer._slice_dims(self.dims.point, self.dims.ndisplay, self.dims.order)

    def _on_add_layer(self, event):
        """Connect new layer events.

        Parameters
        ----------
        event : :class:`napari.layers.Layer`
            Layer to add.
        """
        layer = event.value  # noqa

        # Connect individual layer events to viewer events
        layer.events.interactive.connect(self._update_interactive)
        layer.events.cursor.connect(self._update_cursor)
        layer.events.cursor_size.connect(self._update_cursor_size)
        layer.events.data.connect(self._on_layers_change)
        layer.events.scale.connect(self._on_layers_change)
        layer.events.translate.connect(self._on_layers_change)
        layer.events.rotate.connect(self._on_layers_change)
        layer.events.shear.connect(self._on_layers_change)
        layer.events.affine.connect(self._on_layers_change)
        layer.events.name.connect(self.layers._update_name)

        # Update dims and grid model
        self._on_layers_change(None)
        # Slice current layer based on dims
        self._update_layers(layers=[layer])

        if len(self.layers) == 1:
            self.reset_view()

    def _on_layers_change(self, event):
        if len(self.layers) == 0:
            self.dims.ndim = 2
            self.dims.reset()
        else:
            extent = self.layers.extent
            world = extent.world
            ss = extent.step
            ndim = world.shape[1]
            self.dims.ndim = ndim
            for i in range(ndim):
                self.dims.set_range(i, (world[0, i], world[1, i], ss[i]))
        self.cursor.position = (0,) * self.dims.ndim
        self.events.layers_change()

    def _on_remove_layer(self, event):
        """Disconnect old layer events.

        Parameters
        ----------
        event : napari.utils.event.Event
            Event which will remove a layer.

        Returns
        -------
        layer : :class:`napari.layers.Layer` or list
            The layer that was added (same as input).
        """
        layer = event.value

        # Disconnect all connections from layer
        disconnect_events(layer.events, self)
        disconnect_events(layer.events, self.layers)

        self._on_layers_change(None)

    def add_layer(self, layer: Layer) -> Layer:
        """Add a layer to the viewer.

        Parameters
        ----------
        layer : :class:`napari.layers.Layer`
            Layer to add.

        Returns
        -------
        layer : :class:`napari.layers.Layer` or list
            The layer that was added (same as input).
        """
        # Adding additional functionality inside `add_layer`
        # should be avoided to keep full functionality
        # from adding a layer through the `layers.append`
        # method
        self.layers.append(layer)
        return layer

    def _on_active_layer(self, event):
        """Update viewer state for a new active layer."""
        active_layer = event.value
        if active_layer is None:
            self.help = ""
            self.cursor.style = "standard"
            self.camera.interactive = True
        else:
            self.help = active_layer.help
            self.cursor.style = active_layer.cursor
            self.cursor.size = active_layer.cursor_size
            self.camera.interactive = active_layer.interactive

    def _update_interactive(self, event):
        """Set the viewer interactivity with the `event.interactive` bool."""
        self.camera.interactive = event.interactive

    def _update_cursor(self, event):
        """Set the viewer cursor with the `event.cursor` string."""
        self.cursor.style = event.cursor

    def _update_cursor_size(self, event):
        """Set the viewer cursor_size with the `event.cursor_size` int."""
        self.cursor.size = event.cursor_size

    def _on_cursor_position_change(self, event):
        """Set the layer cursor position."""
        with warnings.catch_warnings():
            # Catch the deprecation warning on layer.position
            warnings.filterwarnings("ignore", message="layer.position is deprecated")
            for layer in self.layers:
                layer.position = self.cursor.position

        # Update status and help bar based on active layer
        active = self.layers.selection.active
        if active is not None:
            self.status = active.get_status(self.cursor.position, world=True)
            self.help = active.help


for _layer in [
    layers.Line,
    layers.Scatter,
    layers.Points,
    layers.Shapes,
    layers.Region,
    layers.InfLine,
    layers.Centroids,
]:
    func = create_add_method(_layer)
    setattr(ViewerModel, func.__name__, func)
