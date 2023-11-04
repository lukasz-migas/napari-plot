"""Viewer model"""
import inspect
import typing as ty
import warnings
from functools import lru_cache

import numpy as np

from napari.components import Dims
from napari.components.tooltip import Tooltip

from napari.components.cursor import Cursor
from napari.components.overlays import Overlay
from napari.components.overlays.text import TextOverlay
from napari.utils._register import create_func as create_add_method
from napari.utils.events import Event, EventedDict, EventedModel, disconnect_events
from napari.utils.key_bindings import KeymapProvider
from napari.utils.mouse_bindings import MousemapProvider
from pydantic import Extra, Field, PrivateAttr
from napari.layers import Layer
from napari_plot import layers as np_layers
from napari_plot.components._viewer_mouse_bindings import (
    box_select,
    box_zoom,
    box_zoom_box,
    box_zoom_horz,
    box_zoom_vert,
    lasso_select,
    polygon_select,
)
from napari_plot.components._viewer_utils import (
    get_layers_x_region_extent,
    get_layers_y_region_extent,
    get_range_extent,
)
from napari_plot.components.axis import Axis
from napari_plot.components.camera import Camera
from napari_plot.components.dragtool import DragMode, DragTool
from napari_plot.components.gridlines import GridLinesOverlay
from napari_plot.components.layerlist import LayerList
from napari_plot.components.tools import BoxTool, PolygonTool
from napari_plot.utils.utilities import get_min_max

DEFAULT_OVERLAYS = {
    "text": TextOverlay,
    "grid_lines": GridLinesOverlay,
}


class ViewerModel(KeymapProvider, MousemapProvider, EventedModel):
    """Viewer containing the rendered scene, layers, and controlling elements
    including dimension sliders, and control bars for color limits.

    Parameters
    ----------
    title : string
        The title of the viewer window.
    """

    # Using allow_mutation=False means these attributes aren't settable and don't
    # have an event emitter associated with them
    cursor: Cursor = Field(default_factory=Cursor, allow_mutation=False)
    dims: Dims = Field(default_factory=Dims, allow_mutation=False)
    layers: LayerList = Field(default_factory=LayerList, allow_mutation=False)
    camera: Camera = Field(default_factory=Camera, allow_mutation=False)
    axis: Axis = Field(default_factory=Axis, allow_mutation=False)
    drag_tool: DragTool = Field(default_factory=DragTool, allow_mutation=False)
    # private track of overlays, only expose the old ones for backward compatibility
    _overlays: EventedDict[str, Overlay] = PrivateAttr(default_factory=EventedDict)

    help: str = ""
    status: ty.Union[str, ty.Dict] = "Ready"
    tooltip: Tooltip = Field(default_factory=Tooltip, allow_mutation=False)
    title: str = "napari-plot"
    theme: str = "dark"

    # 2-tuple indicating height and width
    _canvas_size: ty.Tuple[int, int] = (400, 400)

    # To check if mouse is over canvas to avoid race conditions between
    # different events systems
    mouse_over_canvas: bool = False

    def __init__(self, title="napari_plot"):
        # allow extra attributes during model initialization, useful for mixins
        self.__config__.extra = Extra.allow
        super().__init__(title=title)
        self.__config__.extra = Extra.ignore

        # Add extra events
        self.events.add(layers_change=Event, reset_view=Event, span=Event, clear_canvas=Event)

        # Connect events
        self.cursor.events.position.connect(self._update_status_bar_from_cursor)
        self.layers.events.inserted.connect(self._on_add_layer)
        self.layers.events.removed.connect(self._on_remove_layer)
        self.layers.events.reordered.connect(self._on_layers_change)
        self.layers.events.inserted.connect(self._on_update_extent)
        self.layers.events.removed.connect(self._on_update_extent)
        self.layers.events.connect(self._on_update_extent)
        self.layers.selection.events.active.connect(self._on_active_layer)

        # Set current drag tool
        self.drag_tool.events.active.connect(self._on_update_tool)
        self.drag_tool.active = DragMode.AUTO

        # add overlays
        self._overlays.update({k: v() for k, v in DEFAULT_OVERLAYS.items()})

    @property
    def text_overlay(self) -> TextOverlay:
        """Text overlay"""
        return self._overlays["text"]

    @property
    def grid_lines(self) -> GridLinesOverlay:
        """Text overlay"""
        return self._overlays["grid_lines"]

    def __hash__(self):
        return id(self)

    def __str__(self):
        """Simple string representation"""
        return f"napari_plot.Viewer: {self.title}"

    def _on_update_extent(self, _event=None):
        """Update data extent when there has been a change to the list of layers"""
        extent = self._get_rect_extent()
        # Private extent that is always the same as extent of the data. It is essential that whenever extent is set
        # on the camera, the value of `_extent` is also set as it will be used as a value for resetting axis values
        # if e.g. user uses the `camera.x_range` or `camera.set_x_range`.
        self.camera._extent = extent
        # update extent - must be done after `_extent`
        self.camera.extent = extent

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
        return self.layers.extent.world[:, (0, 1)]

    def _on_update_tool(self, event):
        """Update drag method based on currently active tool."""
        from napari_plot.components.dragtool import BOX_ZOOM_TOOLS, SELECT_TOOLS, DragMode
        from napari_plot.components.tools import Shape

        # if self.drag_tool.tool not in BOX_ZOOM_TOOLS:
        for callback_func in [
            box_zoom_box,
            box_zoom_vert,
            box_zoom_horz,
            box_zoom,
            polygon_select,
            lasso_select,
            box_select,
        ]:
            try:
                index = self.mouse_drag_callbacks.index(callback_func)
                self.mouse_drag_callbacks.pop(index)
            except ValueError:
                pass
        tool = None
        if self.drag_tool.active in BOX_ZOOM_TOOLS:
            tool = self.drag_tool.tool if type(self.drag_tool.tool) == BoxTool else self.drag_tool._box
            if self.drag_tool.active == DragMode.VERTICAL_SPAN:
                tool.shape = Shape.VERTICAL
                self.mouse_drag_callbacks.append(box_zoom_vert)
            elif self.drag_tool.active == DragMode.HORIZONTAL_SPAN:
                tool.shape = Shape.HORIZONTAL
                self.mouse_drag_callbacks.append(box_zoom_horz)
            elif self.drag_tool.active == DragMode.BOX:
                tool.shape = Shape.BOX
                self.mouse_drag_callbacks.append(box_zoom_box)
            elif self.drag_tool.active == DragMode.AUTO:
                tool.shape = Shape.BOX
                self.mouse_drag_callbacks.append(box_zoom)
        elif self.drag_tool.active in SELECT_TOOLS:
            if self.drag_tool.active == DragMode.POLYGON:
                tool = self.drag_tool.tool if type(self.drag_tool.tool) == PolygonTool else self.drag_tool._polygon
                self.mouse_drag_callbacks.append(polygon_select)
            elif self.drag_tool.active == DragMode.LASSO:
                tool = self.drag_tool.tool if type(self.drag_tool.tool) == PolygonTool else self.drag_tool._polygon
                self.mouse_drag_callbacks.append(lasso_select)
            elif self.drag_tool.active == DragMode.BOX_SELECT:
                tool = self.drag_tool.tool if type(self.drag_tool.tool) == BoxTool else self.drag_tool._box
                self.mouse_drag_callbacks.append(box_select)
        self.drag_tool.tool = tool

    def _get_rect_extent(self) -> ty.Tuple[float, ...]:
        """Get data extent"""
        extent = self._sliced_extent_world
        ymin, ymax = get_min_max(extent[:, 0])
        if self.camera.y_range is not None:
            ymin, ymax = self.camera.y_range
        xmin, xmax = get_min_max(extent[:, 1])
        if self.camera.x_range is not None:
            xmin, xmax = self.camera.x_range
        return xmin, xmax, ymin, ymax

    def _get_y_range_extent_for_x(
        self,
        xmin: float,
        xmax: float,
        ymin: float = 0,
        auto_scale: bool = True,
        y_multiplier: float = 1.0,
    ):
        """Calculate range for specified x-axis range."""
        _, _, real_ymin, real_ymax = self._get_rect_extent()
        if auto_scale:
            ymin, ymax = get_range_extent(
                real_ymin, real_ymax, *get_layers_x_region_extent(xmin, xmax, self.layers), ymin
            )
        else:
            ymin, ymax = real_ymin, real_ymax
        return ymin, ymax * y_multiplier

    def _get_x_range_extent_for_y(self, ymin: float, ymax: float, auto_scale: bool = True):
        """Calculate range for specified x-axis range."""
        _, _, real_ymin, real_ymax = self._get_rect_extent()
        if auto_scale:
            ymin, ymax = get_range_extent(
                real_ymin, real_ymax, *get_layers_y_region_extent(ymin, ymax, self.layers), ymin
            )
        else:
            ymin, ymax = real_ymin, real_ymax
        return ymin, ymax

    def reset_view(self, _event=None):
        """Reset the camera view."""
        xmin, xmax, ymin, ymax = self._get_rect_extent()
        self.camera.rect = (xmin, xmax, ymin, ymax)

    def set_x_view(
        self,
        xmin: float,
        xmax: float,
        ymin: float = 0,
        y_multiplier: float = 1.05,
        auto_scale: bool = True,
    ):
        """Set view on specified x-axis"""
        ymin, ymax = self._get_y_range_extent_for_x(xmin, xmax, ymin, y_multiplier=y_multiplier, auto_scale=auto_scale)
        self.camera.rect = (xmin, xmax, ymin, ymax)

    def reset_x_view(self, _event=None):
        """Reset the camera view, but only in the y-axis dimension"""
        xmin, xmax, _, _ = self._get_rect_extent()
        _, _, ymin, ymax = self.camera.rect
        self.camera.rect = (xmin, xmax, ymin, ymax)

    def set_y_view(self, ymin: float, ymax: float):
        """Set view on specified y-axis"""
        xmin, xmax, _, _ = self._get_rect_extent()
        self.camera.rect = (xmin, xmax, ymin, ymax)

    def reset_y_view(self, _event=None):
        """Reset the camera view, but only in the y-axis dimension"""
        _, _, ymin, ymax = self._get_rect_extent()
        xmin, xmax, _, _ = self.camera.rect
        self.camera.rect = (xmin, xmax, ymin, ymax)

    def reset_current_y_view(self, _event=None):
        """Reset y-axis for current selection."""
        xmin, xmax, _, _ = self.camera.rect
        self.set_x_view(xmin, xmax)

    def _update_layers(self, event=None, layers=None):
        """Updates the contained layers.

        Parameters
        ----------
        layers : list of napari.layers.Layer, optional
            List of layers to update. If none provided updates all.
        """
        # layers = layers or self.layers
        # for layer in layers:
        #     layer._slice_dims(self.dims.point, self.dims.ndisplay, self.dims.order)

    def _on_add_layer(self, event):
        """Connect new layer events.

        Parameters
        ----------
        event : :class:`napari.layers.Layer`
            Layer to add.
        """
        layer = event.value  # noqa

        # Connect individual layer events to viewer events
        layer.events.mouse_pan.connect(self._update_mouse_pan)
        layer.events.mouse_zoom.connect(self._update_mouse_zoom)
        layer.events.cursor.connect(self._update_cursor)
        layer.events.cursor_size.connect(self._update_cursor_size)
        layer.events.data.connect(self._on_layers_change)
        layer.events.scale.connect(self._on_layers_change)
        layer.events.translate.connect(self._on_layers_change)
        layer.events.rotate.connect(self._on_layers_change)
        layer.events.shear.connect(self._on_layers_change)
        layer.events.affine.connect(self._on_layers_change)
        layer.events.name.connect(self.layers._update_name)
        layer.events.visible.connect(self._on_update_extent)
        if hasattr(layer.events, "mode"):
            layer.events.mode.connect(self._on_layer_mode_change)

        # Update dims and grid model
        self._on_layers_change(None)
        # Slice current layer based on dims
        self._update_layers(layers=[layer])

        if len(self.layers) == 1:
            self.reset_view()

    def _on_layer_mode_change(self, event):
        if (active := self.layers.selection.active) is not None:
            self.help = active.help

    def _on_layers_change(self, _event=None):
        self.cursor.position = (0,) * 2
        self.events.layers_change()  # TODO: remove

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
            self.camera.mouse_pan = active_layer.mouse_pan
            self.camera.mouse_zoom = active_layer.mouse_zoom
            self._update_status_bar_from_cursor()

    def _update_mouse_pan(self, event):
        """Set the viewer interactive mouse panning"""
        if event.source is self.layers.selection.active:
            self.camera.mouse_pan = event.mouse_pan

    def _update_mouse_zoom(self, event):
        """Set the viewer interactive mouse zoom"""
        if event.source is self.layers.selection.active:
            self.camera.mouse_zoom = event.mouse_zoom

    def _update_cursor(self, event):
        """Set the viewer cursor with the `event.cursor` string."""
        self.cursor.style = event.cursor

    def _update_cursor_size(self, event):
        """Set the viewer cursor_size with the `event.cursor_size` int."""
        self.cursor.size = event.cursor_size

    def _update_status_bar_from_cursor(self, _event=None):
        """Set the layer cursor position."""
        # Update status and help bar based on active layer
        if not self.mouse_over_canvas:
            return
        active = self.layers.selection.active
        if active is not None:
            self.status = active.get_status(
                self.cursor.position,
                view_direction=self.cursor._view_direction,
                dims_displayed=list(self.dims.displayed),
                world=True,
            )

            self.help = active.help
            if self.tooltip.visible:
                self.tooltip.text = active._get_tooltip_text(
                    self.cursor.position,
                    view_direction=self.cursor._view_direction,
                    dims_displayed=list(self.dims.displayed),
                    world=True,
                )
        else:
            self.status = "Ready"


@lru_cache(maxsize=1)
def valid_add_kwargs() -> ty.Dict[str, ty.Set[str]]:
    """Return a dict where keys are layer types & values are valid kwargs."""
    valid = dict()
    for meth in dir(ViewerModel):
        if not meth.startswith("add_") or meth[4:] == "layer":
            continue
        params = inspect.signature(getattr(ViewerModel, meth)).parameters
        valid[meth[4:]] = set(params) - {"self", "kwargs"}
    return valid


for _layer in [
    # napari layers
    np_layers.Points,
    np_layers.Shapes,
    np_layers.Image,
    # napari-plot layers
    np_layers.Line,
    np_layers.Scatter,
    np_layers.Region,
    np_layers.InfLine,
    np_layers.Centroids,
    np_layers.MultiLine,
]:
    func = create_add_method(_layer)
    setattr(ViewerModel, func.__name__, func)
