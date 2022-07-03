"""Viewer model"""
from __future__ import annotations

import typing as ty
import warnings

import numpy as np
from napari.components.cursor import Cursor
from napari.components.text_overlay import TextOverlay
from napari.layers import Layer
from napari.utils._register import create_func as create_add_method
from napari.utils.events import Event, EventedModel, disconnect_events
from napari.utils.key_bindings import KeymapProvider
from napari.utils.mouse_bindings import MousemapProvider
from pydantic import Extra, Field

from .. import layers as np_layers
from ..utils import plot_api as api
from ..utils.utilities import get_min_max
from ._viewer_mouse_bindings import (
    box_select,
    box_zoom,
    box_zoom_box,
    box_zoom_horz,
    box_zoom_vert,
    lasso_select,
    polygon_select,
)
from ._viewer_utils import get_layers_x_region_extent, get_layers_y_region_extent, get_range_extent
from .axis import Axis
from .camera import Camera
from .dragtool import DragTool
from .gridlines import GridLines
from .layerlist import LayerList
from .tools import BoxTool, PolygonTool


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
    layers: LayerList = Field(default_factory=LayerList, allow_mutation=False)
    camera: Camera = Field(default_factory=Camera, allow_mutation=False)
    axis: Axis = Field(default_factory=Axis, allow_mutation=False)
    text_overlay: TextOverlay = Field(default_factory=TextOverlay, allow_mutation=False)
    drag_tool: DragTool = Field(default_factory=DragTool, allow_mutation=False)
    grid_lines: GridLines = Field(default_factory=GridLines, allow_mutation=False)

    help: str = ""
    status: str = "Ready"
    title: str = "napari-plot"
    theme: str = "dark"

    # 2-tuple indicating height and width
    _canvas_size: ty.Tuple[int, int] = (400, 400)

    def __init__(self, title="napari_plot"):
        # allow extra attributes during model initialization, useful for mixins
        self.__config__.extra = Extra.allow
        super().__init__(title=title)
        self.__config__.extra = Extra.ignore

        # Add extra events
        self.events.add(layers_change=Event, reset_view=Event, span=Event, clear_canvas=Event)

        # Connect events
        self.cursor.events.position.connect(self._on_cursor_position_change)
        self.layers.events.inserted.connect(self._on_add_layer)
        self.layers.events.removed.connect(self._on_remove_layer)
        self.layers.events.reordered.connect(self._on_layers_change)
        self.layers.selection.events.active.connect(self._on_active_layer)
        self.layers.events.inserted.connect(self._on_update_extent)
        self.layers.events.removed.connect(self._on_update_extent)
        self.events.layers_change.connect(self._on_update_extent)

        # Set current drag tool
        self.drag_tool.events.active.connect(self._on_update_tool)
        self.drag_tool.active = "auto"

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
        from .dragtool import BOX_ZOOM_TOOLS, SELECT_TOOLS, DragMode
        from .tools import Shape

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
        layer.events.visible.connect(self._on_update_extent)

        # Update dims and grid model
        self._on_layers_change(None)
        # Slice current layer based on dims
        self._update_layers(layers=[layer])

        if len(self.layers) == 1:
            self.reset_view()

    def _on_layers_change(self, _event=None):
        self.cursor.position = (0,) * 2
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

    def _on_cursor_position_change(self, _event=None):
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

    def plot(
        self, y, x: np.ndarray | None = None, fmt: str | None = None, **kwargs
    ) -> np_layers.Line | np_layers.Scatter:
        """Plot y versus x as lines and/or markers.

        Example calls:
            plot(y)
            plot(x, y)
            plot(x, y, [fmt], *, **kwargs)

        Notes
        -----
        Unlike matplotlib, this function only accepts single input so in order to create more than one layer you will
        have to make multiple calls to this function.
        """
        layer_type, layer_kwargs = api.parse_plot(x=x, y=y, fmt=fmt, **kwargs)
        if layer_type == "line":
            return self.add_line(**layer_kwargs)
        return self.add_scatter(**layer_kwargs)

    def scatter(
        self,
        x: np.ndarray,
        y: np.ndarray,
        s: float | np.ndarray = None,
        c=None,
        marker: str = None,
        alpha: float = 1.0,
        scaling: bool = False,
        **kwargs,
    ) -> np_layers.Scatter:
        """A scatter plot of y vs x with varying marker size and/or color."""
        layer_kwargs = api.parse_scatter(x, y, s, c, marker, alpha, **kwargs)
        return self.add_scatter(**layer_kwargs, scaling=scaling)

    def bar(
        self,
        x: float | np.ndarray,
        height: float | np.ndarray,
        width: float | np.ndarray = 0.8,
        bottom: float | np.ndarray | None = None,
        *,
        align: ty.Literal["center", "edge"] = "center",
        **kwargs,
    ) -> ty.Tuple[np_layers.Shapes, np_layers.Centroids | None]:
        """See: https://matplotlib.org/3.5.0/api/_as_gen/matplotlib.pyplot.bar.html"""
        bar_kwargs, error_kwargs = api.parse_bar(x, height, width, bottom, align, **kwargs)
        bar_layer = self.add_shapes(**bar_kwargs)
        # if error_kwargs:
        #     error_layer = self.add_centroids(**error_kwargs)
        return bar_layer

    def barh(
        self,
        y: float | np.ndarray,
        width: float | np.ndarray,
        height: float | np.ndarray = 0.8,
        left: float | np.ndarray | None = None,
        *,
        align: ty.Literal["center", "edge"] = "center",
        **kwargs,
    ) -> ty.Tuple[np_layers.Shapes, np_layers.Centroids | None]:
        """See: https://matplotlib.org/3.5.0/api/_as_gen/matplotlib.pyplot.barh.html"""
        bar_kwargs, error_kwargs = api.parse_bar(
            x=left, height=height, width=width, bottom=y, align=align, orientation="horizontal", **kwargs
        )
        bar_layer = self.add_shapes(**bar_kwargs)
        # if error_kwargs:
        #     error_layer = self.add_centroids(**error_kwargs)
        return bar_layer

    # def hist(
    #     self,
    #     x,
    #     bins=None,
    #     range=None,
    #     density=False,
    #     weights=None,
    #     cumulative=False,
    #     bottom=None,
    #     histtype="bar",
    #     align="mid",
    #     orientation="vertical",
    #     rwidth=None,
    #     log=False,
    #     color=None,
    #     label=None,
    #     stacked=False,
    #     *,
    #     data=None,
    #     **kwargs,
    # ):
    #     """See: https://matplotlib.org/3.5.0/api/_as_gen/matplotlib.pyplot.hist.html"""
    #     raise NotImplementedError("Must implement method")
    #
    # def hist2d(
    #     self, x, y, bins=10, range=None, density=False, weights=None, cmin=None, cmax=None, *, data=None, **kwargs
    # ):
    #     """See: https://matplotlib.org/3.5.0/api/_as_gen/matplotlib.pyplot.hist2d.html"""
    #     raise NotImplementedError("Must implement method")

    def axvspan(self, xmin, xmax, ymin=0, ymax=1, **kwargs):
        """See: https://matplotlib.org/3.5.0/api/_as_gen/matplotlib.pyplot.axvspan.html"""
        layer_kwargs = api.parse_span(xmin, xmax, ymin, ymax, orientation="vertical", **kwargs)
        layer = self.add_region(**layer_kwargs)
        return layer

    def axhspan(self, ymin, ymax, xmin=0, xmax=1, **kwargs):
        """See: https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.axhspan.html"""
        layer_kwargs = api.parse_span(xmin, xmax, ymin, ymax, orientation="horizontal", **kwargs)
        layer = self.add_region(**layer_kwargs)
        return layer

    def axline(self, x=0, xmin=0, xmax=1, **kwargs):
        """See: https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.axline.html"""
        raise NotImplementedError("Must implement method")

    def axvline(self, x=0, xmin=0, xmax=1, **kwargs):
        """See: https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.axvline.html"""
        layer_kwargs = api.parse_axline(x, xmin, xmax, orientation="vertical", **kwargs)
        layer = self.add_inf_line(**layer_kwargs)
        return layer

    def axhline(self, y=0, xmin=0, xmax=1, **kwargs):
        """See: https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.axhline.html"""
        layer_kwargs = api.parse_axline(y, xmin, xmax, orientation="horizontal", **kwargs)
        layer = self.add_inf_line(**layer_kwargs)
        return layer

    # def errorbar(
    #     self,
    #     x,
    #     y,
    #     yerr=None,
    #     xerr=None,
    #     fmt="",
    #     ecolor=None,
    #     elinewidth=None,
    #     capsize=None,
    #     barsabove=False,
    #     lolims=False,
    #     uplims=False,
    #     xlolims=False,
    #     xuplims=False,
    #     errorevery=1,
    #     capthick=None,
    #     *,
    #     data=None,
    #     **kwargs,
    # ):
    #     """See: https://matplotlib.org/3.5.0/api/_as_gen/matplotlib.pyplot.errorbar.html"""
    #     raise NotImplementedError("Must implement method")


def _parse_input_args_for_line(*args) -> ty.Tuple[np.ndarray, np.ndarray]:
    """Parse input arguments for Line plot."""
    if len(args) == 0:
        raise ValueError("You must provide at least input array.")
    elif len(args) == 1:
        y = args[0]
        return np.arange(len(y)), y
    elif len(args) == 2:
        return args[0], args[1]
    else:
        raise ValueError("Expected either one or two arrays.")


def _parse_input_args_for_scatter(*args):
    """Parse input arguments for Scatter plot."""


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
