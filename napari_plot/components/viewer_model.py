"""Viewer model"""
from __future__ import annotations

import inspect
import typing as ty
from functools import lru_cache

import numpy as np

# This cannot be condition to TYPE_CHECKING or the stubgen fails
# with undefined Context.
from app_model.expressions import Context
from napari import layers as n_layers
from napari._pydantic_compat import Extra, Field, PrivateAttr, validator
from napari.components import Dims
from napari.components._layer_slicer import _LayerSlicer
from napari.components.cursor import Cursor, CursorStyle
from napari.components.overlays import BrushCircleOverlay, Overlay, TextOverlay
from napari.components.tooltip import Tooltip
from napari.layers.utils.stack_utils import split_channels
from napari.utils._register import create_func as create_add_method
from napari.utils.colormaps import ensure_colormap
from napari.utils.events import Event, EventedDict, EventedModel, disconnect_events
from napari.utils.key_bindings import KeymapProvider
from napari.utils.misc import is_sequence
from napari.utils.mouse_bindings import MousemapProvider

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
from napari_plot.components.grid_lines import GridLinesOverlay
from napari_plot.components.layerlist import LayerList
from napari_plot.components.tools import BoxTool, PolygonTool
from napari_plot.utils.utilities import get_min_max

EXCLUDE_DICT = {
    "keymap",
    "_mouse_wheel_gen",
    "_mouse_drag_gen",
    "_persisted_mouse_event",
    "mouse_move_callbacks",
    "mouse_drag_callbacks",
    "mouse_wheel_callbacks",
}
EXCLUDE_JSON = EXCLUDE_DICT.union({"layers", "active_layer"})

DEFAULT_OVERLAYS = {
    "text": TextOverlay,
    "grid_lines": GridLinesOverlay,
    "brush_circle": BrushCircleOverlay,
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
    camera: Camera = Field(default_factory=Camera, allow_mutation=False)
    cursor: Cursor = Field(default_factory=Cursor, allow_mutation=False)
    dims: Dims = Field(default_factory=Dims, allow_mutation=False)
    layers: LayerList = Field(default_factory=LayerList, allow_mutation=False)
    axis: Axis = Field(default_factory=Axis, allow_mutation=False)
    drag_tool: DragTool = Field(default_factory=DragTool, allow_mutation=False)

    # Attributes
    help: str = ""
    status: ty.Union[str, dict] = "Ready"
    tooltip: Tooltip = Field(default_factory=Tooltip, allow_mutation=False)
    theme: str = "dark"
    title: str = "napari-plot"

    # private track of overlays, only expose the old ones for backward compatibility
    _overlays: EventedDict[str, Overlay] = PrivateAttr(default_factory=EventedDict)
    _canvas_size: ty.Tuple[int, int] = (400, 400)
    _ctx: Context

    # To check if mouse is over canvas to avoid race conditions between
    # different events systems
    mouse_over_canvas: bool = False

    # Need to use default factory because slicer is not copyable which
    # is required for default values.
    _layer_slicer: _LayerSlicer = PrivateAttr(default_factory=_LayerSlicer)

    def __init__(self, title="napari_plot"):
        # max_depth=0 means don't look for parent contexts.
        from napari_plot._app_model.context import create_context

        # FIXME: just like the LayerList, this object should ideally be created
        # elsewhere.  The app should know about the ViewerModel, but not vice versa.
        self._ctx = create_context(self, max_depth=0)
        # allow extra attributes during model initialization, useful for mixins
        self.__config__.extra = Extra.allow
        super().__init__(title=title)
        self.__config__.extra = Extra.ignore

        # Add extra events
        self.events.add(
            layers_change=Event,
            reset_view=Event,
            span=Event,
            clear_canvas=Event,
        )

        # Connect events
        # dims
        self.dims.events.ndisplay.connect(self._update_layers)
        self.dims.events.ndisplay.connect(self.reset_view)
        self.dims.events.order.connect(self._update_layers)
        self.dims.events.order.connect(self.reset_view)
        self.dims.events.point.connect(self._update_layers)
        self.dims.events.current_step.connect(self._update_layers)
        self.dims.events.margin_left.connect(self._update_layers)
        self.dims.events.margin_right.connect(self._update_layers)
        # cursor
        self.cursor.events.position.connect(self.update_status_from_cursor)
        # layers
        self.layers.events.inserted.connect(self._on_add_layer)
        self.layers.events.removed.connect(self._on_remove_layer)
        self.layers.events.reordered.connect(self._on_layers_change)
        self.layers.events.inserted.connect(self._on_update_extent)
        self.layers.events.removed.connect(self._on_update_extent)
        self.layers.events.connect(self._on_update_extent)
        self.layers.selection.events.active.connect(self._on_active_layer)
        # drag
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

    @property
    def _brush_circle_overlay(self):
        return self._overlays["brush_circle"]

    @validator("theme", allow_reuse=True)
    def _valid_theme(cls, v):
        from napari.utils.theme import available_themes, is_theme_available

        if not is_theme_available(v):
            themes = ", ".join(available_themes())
            raise ValueError(f"Theme '{v}' not found; options are {themes}.")
        return v

    def json(self, **kwargs):
        """Serialize to json."""
        # Manually exclude the layer list and active layer which cannot be serialized at this point
        # and mouse and keybindings don't belong on model
        # https://github.com/samuelcolvin/pydantic/pull/2231
        # https://github.com/samuelcolvin/pydantic/issues/660#issuecomment-642211017
        exclude = kwargs.pop("exclude", set())
        exclude = exclude.union(EXCLUDE_JSON)
        return super().json(exclude=exclude, **kwargs)

    def dict(self, **kwargs):
        """Convert to a dictionary."""
        # Manually exclude the layer list and active layer which cannot be serialized at this point
        # and mouse and keybindings don't belong on model
        # https://github.com/samuelcolvin/pydantic/pull/2231
        # https://github.com/samuelcolvin/pydantic/issues/660#issuecomment-642211017
        exclude = kwargs.pop("exclude", set())
        exclude = exclude.union(EXCLUDE_DICT)
        return super().dict(exclude=exclude, **kwargs)

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

    @property
    def _sliced_extent_world_augmented(self) -> np.ndarray:
        """Extent of layers in world coordinates after slicing.

        D is either 2 or 3 depending on if the displayed data is 2D or 3D.

        Returns
        -------
        sliced_extent_world : array, shape (2, D)
        """
        # if not layers are present, assume image-like with dimensions of size 512
        if len(self.layers) == 0:
            return np.vstack([np.full(self.dims.ndim, -0.5), np.full(self.dims.ndim, 511.5)])
        return self.layers._extent_world_augmented[:, self.dims.displayed]

    def reset_view(self, _event: Event = None) -> None:
        """Reset the camera view."""
        xmin, xmax, ymin, ymax = self._get_rect_extent()
        self.camera.rect = (xmin, xmax, ymin, ymax)

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
                real_ymin,
                real_ymax,
                *get_layers_x_region_extent(xmin, xmax, self.layers),
                ymin,
            )
        else:
            ymin, ymax = real_ymin, real_ymax
        return ymin, ymax * y_multiplier

    def _get_x_range_extent_for_y(self, ymin: float, ymax: float, auto_scale: bool = True):
        """Calculate range for specified x-axis range."""
        _, _, real_ymin, real_ymax = self._get_rect_extent()
        if auto_scale:
            ymin, ymax = get_range_extent(
                real_ymin,
                real_ymax,
                *get_layers_y_region_extent(ymin, ymax, self.layers),
                ymin,
            )
        else:
            ymin, ymax = real_ymin, real_ymax
        return ymin, ymax

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

    def _on_update_tool(self, event):
        """Update drag method based on currently active tool."""
        from napari_plot.components.dragtool import (
            BOX_ZOOM_TOOLS,
            SELECT_TOOLS,
            DragMode,
        )
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
            if tool and self.drag_tool.active == DragMode.VERTICAL_SPAN:
                tool.shape = Shape.VERTICAL
                self.mouse_drag_callbacks.append(box_zoom_vert)
            elif tool and self.drag_tool.active == DragMode.HORIZONTAL_SPAN:
                tool.shape = Shape.HORIZONTAL
                self.mouse_drag_callbacks.append(box_zoom_horz)
            elif tool and self.drag_tool.active == DragMode.BOX:
                tool.shape = Shape.BOX
                self.mouse_drag_callbacks.append(box_zoom_box)
            elif tool and self.drag_tool.active == DragMode.AUTO:
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

    def _on_layer_reload(self, event: Event) -> None:
        self._layer_slicer.submit(layers=[event.layer], dims=self.dims, force=True)

    def _update_layers(self, *, layers=None):
        """Updates the contained layers.

        Parameters
        ----------
        layers : list of napari.layers.Layer, optional
            List of layers to update. If none provided updates all.
        """
        layers = layers or self.layers
        self._layer_slicer.submit(layers=layers, dims=self.dims)
        # If the currently selected layer is sliced asynchronously, then the value
        # shown with this position may be incorrect. See the discussion for more details:
        # https://github.com/napari/napari/pull/5377#discussion_r1036280855
        position = list(self.cursor.position)
        if len(position) < self.dims.ndim:
            # cursor dimensionality is outdated — reset to correct dimension
            position = [0.0] * self.dims.ndim
        for ind in self.dims.order[: -self.dims.ndisplay]:
            position[ind] = self.dims.point[ind]
        self.cursor.position = tuple(position)

    def _on_active_layer(self, event):
        """Update viewer state for a new active layer."""
        active_layer = event.value
        if active_layer is None:
            for layer in self.layers:
                layer.update_transform_box_visibility(False)
                layer.update_highlight_visibility(False)
            self.help = ""
            self.cursor.style = CursorStyle.STANDARD
            self.camera.mouse_pan = True
            self.camera.mouse_zoom = True
        else:
            active_layer.update_transform_box_visibility(True)
            active_layer.update_highlight_visibility(True)
            for layer in self.layers:
                if layer != active_layer:
                    layer.update_transform_box_visibility(False)
                    layer.update_highlight_visibility(False)
            self.help = active_layer.help
            self.cursor.style = active_layer.cursor
            self.cursor.size = active_layer.cursor_size
            self.camera.mouse_pan = active_layer.mouse_pan
            self.camera.mouse_zoom = active_layer.mouse_zoom
            self.update_status_from_cursor()

    def _on_layers_change(self, _event=None):
        self.cursor.position = (0,) * 2
        self.events.layers_change()  # TODO: remove

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

    def _update_async(self, event: Event) -> None:
        """Set layer slicer to force synchronous if async is disabled."""
        self._layer_slicer._force_sync = not event.value

    def _calc_status_from_cursor(
        self,
    ) -> ty.Optional[tuple[ty.Union[str, ty.Dict], str]]:
        if not self.mouse_over_canvas:
            return None
        active = self.layers.selection.active
        if active is not None and active._loaded:
            status = active.get_status(
                self.cursor.position,
                view_direction=self.cursor._view_direction,
                dims_displayed=list(self.dims.displayed),
                world=True,
            )

            if self.tooltip.visible:
                tooltip_text = active._get_tooltip_text(
                    np.asarray(self.cursor.position),
                    view_direction=np.asarray(self.cursor._view_direction),
                    dims_displayed=list(self.dims.displayed),
                    world=True,
                )
            else:
                tooltip_text = ""

            return status, tooltip_text
        return "Ready", ""

    def update_status_from_cursor(self):
        """Update the status and tooltip from the cursor position."""
        status = self._calc_status_from_cursor()
        if status is not None:
            self.status, self.tooltip.text = status
        if (active := self.layers.selection.active) is not None:
            self.help = active.help

    def _on_add_layer(self, event):
        """Connect new layer events.

        Parameters
        ----------
        event : :class:`napari.layers.Layer`
            Layer to add.
        """
        layer = event.value

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
        layer.events.reload.connect(self._on_layer_reload)
        layer.events.visible.connect(self._on_update_extent)
        if hasattr(layer.events, "mode"):
            layer.events.mode.connect(self._on_layer_mode_change)
        self._layer_help_from_mode(layer)

        # Update dims and grid model
        self._on_layers_change(None)
        # Slice current layer based on dims
        self._update_layers(layers=[layer])

        if len(self.layers) == 1:
            self.reset_view()
            self.dims._go_to_center_step()

    @staticmethod
    def _layer_help_from_mode(layer: n_layers.Layer):
        """Update layer help text base on layer mode."""
        from napari.layers.image._image_key_bindings import image_fun_to_mode
        from napari.layers.labels._labels_key_bindings import labels_fun_to_mode
        from napari.layers.points._points_key_bindings import points_fun_to_mode
        from napari.layers.shapes._shapes_key_bindings import shapes_fun_to_mode
        from napari.settings import get_settings

        from napari_plot.layers.centroids._centroids_key_bindings import (
            centroids_fun_to_mode,
        )
        from napari_plot.layers.infline._infline_key_bindings import infline_fun_to_mode
        from napari_plot.layers.line._line_key_bindings import line_fun_to_mode
        from napari_plot.layers.multiline._multiline_key_bindings import (
            multiline_fun_to_mode,
        )
        from napari_plot.layers.region._region_key_bindings import region_fun_to_mode
        from napari_plot.layers.scatter._scatter_key_bindings import scatter_fun_to_mode

        # from napari.layers.surface._surface_key_bindings import surface_fun_to_mode
        # from napari.layers.tracks._tracks_key_bindings import tracks_fun_to_mode
        # from napari.layers.vectors._vectors_key_bindings import vectors_fun_to_mode
        from napari_plot.utils.action_manager import action_manager

        layer_to_func_and_mode: dict[type[n_layers.Layer], list] = {
            n_layers.Points: points_fun_to_mode,
            n_layers.Labels: labels_fun_to_mode,
            n_layers.Shapes: shapes_fun_to_mode,
            n_layers.Image: image_fun_to_mode,
            # n_layers.Vectors: vectors_fun_to_mode,
            # n_layers.Surface: surface_fun_to_mode,
            # n_layers.Tracks: tracks_fun_to_mode,
            np_layers.Line: line_fun_to_mode,
            np_layers.Scatter: scatter_fun_to_mode,
            np_layers.Region: region_fun_to_mode,
            np_layers.InfLine: infline_fun_to_mode,
            np_layers.Centroids: centroids_fun_to_mode,
            np_layers.MultiLine: multiline_fun_to_mode,
        }

        help_li = []
        shortcuts = get_settings().shortcuts.shortcuts

        for fun, mode_ in layer_to_func_and_mode.get(layer.__class__, []):
            if mode_ == layer.mode:
                continue
            action_name = f"napari_plot:{fun.__name__}"
            action = action_manager._actions.get(action_name, None)
            if action:
                desc = action.description.lower()
                if not shortcuts.get(action_name, []):
                    continue
                help_li.append(f"use <{shortcuts[action_name][0]}> for {desc}")
        layer.help = ", ".join(help_li)

    def _on_layer_mode_change(self, event):
        self._layer_help_from_mode(event.source)
        if (active := self.layers.selection.active) is not None:
            self.help = active.help

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

        # Clean up overlays
        for overlay in list(layer._overlays):
            del layer._overlays[overlay]

        self._on_layers_change(None)

    def add_layer(self, layer: n_layers.Layer) -> n_layers.Layer:
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

    def add_image(
        self,
        data=None,
        *,
        channel_axis=None,
        affine=None,
        axis_labels=None,
        attenuation=0.05,
        blending=None,
        cache=True,
        colormap=None,
        contrast_limits=None,
        custom_interpolation_kernel_2d=None,
        depiction="volume",
        experimental_clipping_planes=None,
        gamma=1.0,
        interpolation2d="nearest",
        interpolation3d="linear",
        iso_threshold=None,
        metadata=None,
        multiscale=None,
        name=None,
        opacity=1.0,
        plane=None,
        projection_mode="none",
        rendering="mip",
        rgb=None,
        rotate=None,
        scale=None,
        shear=None,
        translate=None,
        units=None,
        visible=True,
    ) -> ty.Union[n_layers.Image, list[n_layers.Image]]:
        """Add one or more Image layers to the layer list.

        Parameters
        ----------
        data : array or list of array
            Image data. Can be N >= 2 dimensional. If the last dimension has length
            3 or 4 can be interpreted as RGB or RGBA if rgb is `True`. If a
            list and arrays are decreasing in shape then the data is treated as
            a multiscale image. Please note multiscale rendering is only
            supported in 2D. In 3D, only the lowest resolution scale is
            displayed.
        channel_axis : int, optional
            Axis to expand image along. If provided, each channel in the data
            will be added as an individual image layer. In channel_axis mode,
            other parameters MAY be provided as lists. The Nth value of the list
            will be applied to the Nth channel in the data. If a single value
            is provided, it will be broadcast to all Layers.
            All parameters except data, rgb, and multiscale can be provided as
            list of values. If a list is provided, it must be the same length as
            the axis that is being expanded as channels.
        affine : n-D array or napari.utils.transforms.Affine
            (N+1, N+1) affine transformation matrix in homogeneous coordinates.
            The first (N, N) entries correspond to a linear transform and
            the final column is a length N translation vector and a 1 or a
            napari `Affine` transform object. Applied as an extra transform on
            top of the provided scale, rotate, and shear values.
        axis_labels : tuple of str
            Dimension names of the layer data.
            If not provided, axis_labels will be set to (..., 'axis -2', 'axis -1').
        attenuation : float or list of float
            Attenuation rate for attenuated maximum intensity projection.
        blending : str or list of str
            One of a list of preset blending modes that determines how RGB and
            alpha values of the layer visual get mixed. Allowed values are
            {'translucent', 'translucent_no_depth', 'additive', 'minimum', 'opaque'}.
        cache : bool or list of bool
            Whether slices of out-of-core datasets should be cached upon
            retrieval. Currently, this only applies to dask arrays.
        colormap : str, napari.utils.Colormap, tuple, dict, list or list of these types
            Colormaps to use for luminance images. If a string, it can be the name
            of a supported colormap from vispy or matplotlib or the name of
            a vispy color or a hexadecimal RGB color representation.
            If a tuple, the first value must be a string to assign as a name to a
            colormap and the second item must be a Colormap. If a dict, the key must
            be a string to assign as a name to a colormap and the value must be a
            Colormap.
        contrast_limits : list (2,)
            Intensity value limits to be used for determining the minimum and maximum colormap bounds for
            luminance images. If not passed, they will be calculated as the min and max intensity value of
            the image.
        custom_interpolation_kernel_2d : np.ndarray
            Convolution kernel used with the 'custom' interpolation mode in 2D rendering.
        depiction : str or list of str
            3D Depiction mode. Must be one of {'volume', 'plane'}.
            The default value is 'volume'.
        experimental_clipping_planes : list of dicts, list of ClippingPlane, or ClippingPlaneList
            Each dict defines a clipping plane in 3D in data coordinates.
            Valid dictionary keys are {'position', 'normal', and 'enabled'}.
            Values on the negative side of the normal are discarded if the plane is enabled.
        gamma : float or list of float
            Gamma correction for determining colormap linearity; defaults to 1.
        interpolation2d : str or list of str
            Interpolation mode used by vispy for rendering 2d data.
            Must be one of our supported modes.
            (for list of supported modes see Interpolation enum)
            'custom' is a special mode for 2D interpolation in which a regular grid
            of samples is taken from the texture around a position using 'linear'
            interpolation before being multiplied with a custom interpolation kernel
            (provided with 'custom_interpolation_kernel_2d').
        interpolation3d : str or list of str
            Same as 'interpolation2d' but for 3D rendering.
        iso_threshold : float or list of float
            Threshold for isosurface.
        metadata : dict or list of dict
            Layer metadata.
        multiscale : bool
            Whether the data is a multiscale image or not. Multiscale data is
            represented by a list of array-like image data. If not specified by
            the user and if the data is a list of arrays that decrease in shape,
            then it will be taken to be multiscale. The first image in the list
            should be the largest. Please note multiscale rendering is only
            supported in 2D. In 3D, only the lowest resolution scale is
            displayed.
        name : str or list of str
            Name of the layer.
        opacity : float or list
            Opacity of the layer visual, between 0.0 and 1.0.
        plane : dict or SlicingPlane
            Properties defining plane rendering in 3D. Properties are defined in
            data coordinates. Valid dictionary keys are
            {'position', 'normal', 'thickness', and 'enabled'}.
        projection_mode : str
            How data outside the viewed dimensions, but inside the thick Dims slice will
            be projected onto the viewed dimensions. Must fit to cls._projectionclass
        rendering : str or list of str
            Rendering mode used by vispy. Must be one of our supported
            modes. If a list then must be same length as the axis that is being
            expanded as channels.
        rgb : bool, optional
            Whether the image is RGB or RGBA if rgb. If not
            specified by user, but the last dimension of the data has length 3 or 4,
            it will be set as `True`. If `False`, the image is interpreted as a
            luminance image.
        rotate : float, 3-tuple of float, n-D array or list.
            If a float, convert into a 2D rotation matrix using that value as an
            angle. If 3-tuple, convert into a 3D rotation matrix, using a yaw,
            pitch, roll convention. Otherwise, assume an nD rotation. Angles are
            assumed to be in degrees. They can be converted from radians with
            'np.degrees' if needed.
        scale : tuple of float or list of tuple of float
            Scale factors for the layer.
        shear : 1-D array or list.
            A vector of shear values for an upper triangular n-D shear matrix.
        translate : tuple of float or list of tuple of float
            Translation values for the layer.
        units : tuple of str or pint.Unit, optional
            Units of the layer data in world coordinates.
            If not provided, the default units are assumed to be pixels.
        visible : bool or list of bool
            Whether the layer visual is currently being displayed.

        Returns
        -------
        layer : :class:`napari.layers.Image` or list
            The newly-created image layer or list of image layers.
        """

        if colormap is not None:
            # standardize colormap argument(s) to Colormaps, and make sure they
            # are in AVAILABLE_COLORMAPS.  This will raise one of many various
            # errors if the colormap argument is invalid.  See
            # ensure_colormap for details
            if isinstance(colormap, list):
                colormap = [ensure_colormap(c) for c in colormap]
            else:
                colormap = ensure_colormap(colormap)

        # doing this here for IDE/console autocompletion in add_image function.
        kwargs = {
            "rgb": rgb,
            "axis_labels": axis_labels,
            "colormap": colormap,
            "contrast_limits": contrast_limits,
            "gamma": gamma,
            "interpolation2d": interpolation2d,
            "interpolation3d": interpolation3d,
            "rendering": rendering,
            "depiction": depiction,
            "iso_threshold": iso_threshold,
            "attenuation": attenuation,
            "name": name,
            "metadata": metadata,
            "scale": scale,
            "translate": translate,
            "rotate": rotate,
            "shear": shear,
            "affine": affine,
            "opacity": opacity,
            "blending": blending,
            "visible": visible,
            "multiscale": multiscale,
            "cache": cache,
            "plane": plane,
            "experimental_clipping_planes": experimental_clipping_planes,
            "custom_interpolation_kernel_2d": custom_interpolation_kernel_2d,
            "projection_mode": projection_mode,
            "units": units,
        }

        # these arguments are *already* iterables in the single-channel case.
        iterable_kwargs = {
            "scale",
            "translate",
            "rotate",
            "shear",
            "affine",
            "contrast_limits",
            "metadata",
            "experimental_clipping_planes",
            "custom_interpolation_kernel_2d",
            "axis_labels",
            "units",
        }

        if channel_axis is None:
            kwargs["colormap"] = kwargs["colormap"] or "gray"
            kwargs["blending"] = kwargs["blending"] or "translucent_no_depth"
            # Helpful message if someone tries to add multi-channel kwargs,
            # but forget the channel_axis arg
            for k, v in kwargs.items():
                if k not in iterable_kwargs and is_sequence(v):
                    raise TypeError(f"Received sequence for argument '{k}', did you mean to specify a 'channel_axis'? ")
            layer = n_layers.Image(data, **kwargs)
            self.layers.append(layer)

            return layer

        layerdata_list = split_channels(data, channel_axis, **kwargs)
        layer_list = [n_layers.Image(image, **i_kwargs) for image, i_kwargs, _ in layerdata_list]
        self.layers.extend(layer_list)
        return layer_list


@lru_cache(maxsize=1)
def valid_add_kwargs() -> ty.Dict[str, ty.Set[str]]:
    """Return a dict where keys are layer types & values are valid kwargs."""
    valid = {}
    for meth in dir(ViewerModel):
        if not meth.startswith("add_") or meth[4:] == "layer":
            continue
        params = inspect.signature(getattr(ViewerModel, meth)).parameters
        valid[meth[4:]] = set(params) - {"self", "kwargs"}
    return valid


for _layer in [
    # napari layers
    n_layers.Points,
    n_layers.Shapes,
    n_layers.Image,
    n_layers.Labels,
    # n_layers.Tracks,  # 3d
    # n_layers.Vectors,  # 3d
    # n_layers.Surface,  # 3d
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
