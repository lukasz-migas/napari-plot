"""Viewer model"""

from __future__ import annotations

import inspect
from collections.abc import Sequence
from contextlib import suppress
from functools import cached_property, lru_cache
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal

import numpy as np

# This cannot be condition to TYPE_CHECKING or the stubgen fails
# with undefined Context.
from app_model.expressions import Context
from napari import layers as n_layers
from napari.components import Dims
from napari.components._layer_slicer import _LayerSlicer
from napari.components.cursor import Cursor, CursorStyle
from napari.components.overlays import BrushCircleOverlay, TextOverlay
from napari.components.tooltip import Tooltip
from napari.layers.utils.stack_utils import split_channels
from napari.utils._register import create_func as create_add_method
from napari.utils.colormaps import ensure_colormap
from napari.utils.events import Event, EventedDictNamespace, EventedModel, EventEmitter, disconnect_events
from napari.utils.interactions import _discard_active_generators
from napari.utils.key_bindings import KeymapProvider
from napari.utils.misc import camel_to_snake, is_sequence
from napari.utils.mouse_bindings import MousemapProviderPydantic
from numpy.typing import ArrayLike
from pydantic import Field, PrivateAttr, field_validator

from napari_plot import layers as np_layers, stats
from napari_plot.components._viewer_mouse_bindings import (
    box_select,
    box_zoom_auto,
    box_zoom_auto_trigger,
    box_zoom_box,
    box_zoom_horz,
    box_zoom_vert,
    lasso_select,
    polygon_select,
)
from napari_plot.components._viewer_utils import (
    get_layers_region_extent,
    get_layers_x_region_extent,
    get_layers_y_region_extent,
    get_range_extent,
)
from napari_plot.components.axis import Axis, AxisScale, transform_axis_values
from napari_plot.components.camera import Camera
from napari_plot.components.canvas import PlotCanvas, PlotGridCell
from napari_plot.components.colorbar import ColorBar
from napari_plot.components.crosshair import CrosshairOverlay
from napari_plot.components.dragtool import DragMode, DragTool
from napari_plot.components.grid_lines import GridLinesOverlay
from napari_plot.components.hover import HoverOverlay
from napari_plot.components.joint_grid import joint_panel
from napari_plot.components.layerlist import LayerList
from napari_plot.components.legend import (
    ColorLike as LegendColorLike,
    LegendInput,
    LegendOverlay,
    legend_entries_from_layers,
    legend_entries_from_points,
)
from napari_plot.components.scene import Scene
from napari_plot.components.tools import BoxTool, PolygonTool
from napari_plot.utils.hover import HoverInfo, PixelMapper, format_coordinates
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
    "legend": LegendOverlay,
    "crosshair": CrosshairOverlay,
    "hover": HoverOverlay,
}

LEGEND_LAYER_EVENTS = (
    "data",
    "name",
    "visible",
    "color",
    "width",
    "fill_color",
    "face_color",
    "border_color",
    "outline_color",
    "symbol",
    "size",
    "orientation",
    "properties",
    "features",
)


def _create_custom_add_method(layer_type):
    """Create an ``add_*`` method for custom napari-plot layers.

    napari's dynamic helper compiles a function with a return annotation
    pointing at the fully-qualified layer class. That works for built-in
    napari layers because ``napari`` is injected into the exec namespace,
    but it fails for local layer classes such as
    ``napari_plot.layers.line.line.Line``. For custom layers we can avoid the
    exec-based path entirely and expose the same public signature via
    ``__signature__``.
    """

    name = f"add_{camel_to_snake(layer_type.__name__)}"
    signature = inspect.signature(layer_type)
    signature_with_self = signature.replace(
        parameters=[
            inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            *signature.parameters.values(),
        ],
        return_annotation=layer_type,
    )

    def _add_layer(self, *args, **kwargs):
        layer = layer_type(*args, **kwargs)
        self.layers.append(layer)
        return layer

    _add_layer.__name__ = name
    _add_layer.__qualname__ = f"ViewerModel.{name}"
    _add_layer.__doc__ = getattr(layer_type, "__doc__", None)
    _add_layer.__signature__ = signature_with_self
    return _add_layer


def _create_stats_method(func):
    """Expose a ``napari_plot.stats`` function as a viewer method with the same signature and docs."""
    signature = inspect.signature(func)
    parameters = list(signature.parameters.values())
    parameters[0] = parameters[0].replace(name="self")

    def _plot(self, *args, **kwargs):
        return func(self, *args, **kwargs)

    _plot.__name__ = func.__name__
    _plot.__qualname__ = f"ViewerModel.{func.__name__}"
    _plot.__doc__ = func.__doc__
    _plot.__signature__ = signature.replace(parameters=parameters)
    return _plot


class _StatsMethod:
    """Bind a stats function lazily while preserving its signature and docstring."""

    def __init__(self, name: str) -> None:
        self._name = name

    @cached_property
    def _method(self) -> Any:
        return _create_stats_method(getattr(stats, self._name))

    def __get__(self, instance: ViewerModel | None, owner: type[ViewerModel]) -> Any:
        return self._method.__get__(instance, owner)


def _pad_by_pixels(lower: float, upper: float, pad_px: float, size_px: float) -> tuple[float, float]:
    """Widen ``lower``-``upper`` so ``pad_px`` screen pixels fit on each side when shown across ``size_px`` pixels."""
    span = upper - lower
    if pad_px <= 0 or not np.isfinite(span) or span <= 0:
        return lower, upper
    usable = max(float(size_px) - 2 * pad_px, 1.0)
    pad = span * pad_px / usable
    # keep strictly positive data positive so the extent stays valid if an axis is switched to log scale
    padded_lower = lower if 0 < lower <= pad else lower - pad
    return padded_lower, upper + pad


def _plot_data(x: Any, y: Any | None = None) -> np.ndarray:
    """Return validated ``(x, y)`` rows for plotting helpers."""
    if y is None:
        y_values = np.asarray(x)
        x_values = np.arange(y_values.size)
    else:
        x_values = np.asarray(x)
        y_values = np.asarray(y)
    if x_values.ndim != 1 or y_values.ndim != 1:
        raise ValueError("Plot coordinates must be one-dimensional.")
    if x_values.shape != y_values.shape:
        raise ValueError("x and y must have the same shape.")
    return np.column_stack((x_values, y_values))


def _plot_color(kwargs: dict[str, Any], target: str) -> None:
    """Accept `color` on the plotting facade for layers with a named primary color."""
    if "color" in kwargs:
        if target in kwargs:
            raise TypeError(f"Pass only one of color and {target}.")
        kwargs[target] = kwargs.pop("color")


def _band_rows(t: ArrayLike, lower: ArrayLike, upper: ArrayLike) -> np.ndarray:
    coordinates = np.asarray(t)
    if coordinates.ndim != 1:
        raise ValueError("Band coordinates must be one-dimensional.")
    bounds = []
    for bound in (lower, upper):
        values = np.asarray(bound)
        if values.ndim == 0:
            values = np.broadcast_to(values, coordinates.shape)
        if values.shape != coordinates.shape:
            raise ValueError("Band bounds must be scalars or have the same shape as the coordinates.")
        bounds.append(values)
    return np.column_stack((coordinates, *bounds))


# layer events that change where a layer's data is drawn
_LAYER_GEOMETRY_EVENTS = frozenset({"data", "scale", "translate", "rotate", "shear", "affine"})
# layer events (re-emitted by the layer list) that never change the data extent; the geometry events are handled by
# `ViewerModel._on_layers_change`
_EXTENT_NEUTRAL_EVENTS = _LAYER_GEOMETRY_EVENTS | frozenset(
    {
        "thumbnail", "color", "highlight", "set_data", "loaded", "name", "opacity", "blending", "status", "help",
        "cursor", "cursor_size", "interactive", "mouse_pan", "mouse_zoom", "editable", "fill_color", "border_color",
        "border_width", "method", "stream", "selected", "reordered", "moving", "moved", "inserting", "removing",
    }
)  # fmt: skip


class ViewerModel(KeymapProvider, MousemapProviderPydantic, EventedModel):
    """Viewer containing the rendered scene, layers, and controlling elements
    including dimension sliders, and control bars for color limits.

    Parameters
    ----------
    title : string
        The title of the viewer window.
    """

    __non_evented_properties__ = EventedModel.__non_evented_properties__ | {"camera"}

    # Using frozen=True means these attributes aren't settable and don't
    # have an event emitter associated with them
    scene: Scene = Field(default_factory=Scene, frozen=True)
    canvas: PlotCanvas = Field(
        default_factory=lambda: PlotCanvas(size=(400, 400), overlays=EventedDictNamespace()), frozen=True
    )
    cursor: Cursor = Field(default_factory=Cursor, frozen=True)
    dims: Dims = Field(default_factory=Dims, frozen=True)
    layers: LayerList = Field(default_factory=LayerList, frozen=True)
    axis: Axis = Field(default_factory=Axis, frozen=True)
    colorbar: ColorBar = Field(default_factory=ColorBar, frozen=True)
    drag_tool: DragTool = Field(default_factory=DragTool, frozen=True)

    # Attributes
    help: str = ""
    autoscale: bool = True
    margins: tuple[float, float] = (0.0, 0.0)
    status: str | dict = "Ready"
    tooltip: Tooltip = Field(default_factory=Tooltip, frozen=True)
    theme: str = "dark"
    title: str = "napari-plot"

    # private track of overlays, only expose the old ones for backward compatibility
    _explicit_axis_labels: set[str] = PrivateAttr(default_factory=set)
    _setting_axis_labels: bool = PrivateAttr(False)
    _ctx: Context

    # To check if mouse is over canvas to avoid race conditions between
    # different events systems
    mouse_over_canvas: bool = False

    # Need to use default factory because slicer is not copyable which
    # is required for default values.
    _layer_slicer: _LayerSlicer = PrivateAttr(default_factory=_LayerSlicer)
    _legend_source_layers: list[n_layers.Layer] = PrivateAttr(default_factory=list)
    _colorbar_sources: dict[tuple[int, int] | None, n_layers.Layer] = PrivateAttr(default_factory=dict)
    _cell_colorbars: dict[tuple[int, int], ColorBar] = PrivateAttr(default_factory=dict)
    _text_overlay_names: list[str] = PrivateAttr(default_factory=list)
    # joint-grid panel under the cursor ("joint", "top" or "right"; None outside joint mode)
    _cursor_panel: str | None = PrivateAttr(None)

    def __init__(self, title="napari_plot"):
        # max_depth=0 means don't look for parent contexts.
        from napari_plot._app_model.context import create_context

        # FIXME: just like the LayerList, this object should ideally be created
        # elsewhere.  The app should know about the ViewerModel, but not vice versa.
        self._ctx = create_context(self, max_depth=0)
        # allow extra attributes during model initialization, useful for mixins
        self.model_config["extra"] = "allow"
        super().__init__(title=title)
        self.model_config["extra"] = "ignore"

        # Add extra events
        self.events.add(
            layers_change=Event,
            reset_view=Event,
            span=Event,
            selection=Event,
            clear_canvas=Event,
            colorbars_change=Event,
        )
        self.events.theme.connect(self.canvas._update_bgcolor_from_viewer)
        self.canvas._update_bgcolor_from_viewer(Event("theme", value=self.theme))
        self.axis.events.x_label.connect(self._on_axis_label_changed)
        self.axis.events.y_label.connect(self._on_axis_label_changed)
        self.events.margins.connect(self._on_update_extent)
        self.events.autoscale.connect(self._on_autoscale_changed)

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
        self.layers.events.connect(self._on_layer_list_event)
        for name in ("enabled", "joint", "joint_top", "joint_right"):
            getattr(self.canvas.grid.events, name).connect(self._on_update_extent)
        self.layers.selection.events.active.connect(self._on_active_layer)
        # drag
        self.drag_tool.events.active.connect(self._on_update_tool)
        self.drag_tool.active = DragMode.AUTO

        # add overlays
        self._overlays.update({k: v() for k, v in DEFAULT_OVERLAYS.items()})
        self.layers.events.inserted.connect(self._on_legend_layers_change)
        self.layers.events.removed.connect(self._on_legend_layers_change)
        self.layers.events.reordered.connect(self._on_legend_layers_change)
        self._refresh_legend_source_connections()
        # crosshair and hover readout
        self.cursor.events.position.connect(self._update_hover)
        self.events.mouse_over_canvas.connect(self._update_hover)
        for events in (self.crosshair.events, self.hover.events):
            events.visible.connect(self._update_hover)
        self.crosshair.events.snap_to_data.connect(self._update_hover)
        self.hover.events.formatter.connect(self._update_hover)

    @property
    def camera(self) -> Camera:
        """Return the camera owned by the plot scene."""
        return self.scene.camera

    @camera.setter
    def camera(self, _value: Camera) -> None:
        raise ValueError("Field is frozen")

    @property
    def _overlays(self) -> EventedDictNamespace:
        return self.canvas.overlays

    @property
    def _canvas_size(self) -> tuple[int, int]:
        return self.canvas.size

    @_canvas_size.setter
    def _canvas_size(self, size: tuple[int, int]) -> None:
        self.canvas.size = size

    @property
    def text_overlay(self) -> TextOverlay:
        """Text overlay"""
        return self._overlays["text"]

    @property
    def grid_lines(self) -> GridLinesOverlay:
        """Text overlay"""
        return self._overlays["grid_lines"]

    @property
    def legend(self) -> LegendOverlay:
        """Canvas legend overlay."""
        return self._overlays["legend"]

    @property
    def crosshair(self) -> CrosshairOverlay:
        """Crosshair overlay (hidden by default)."""
        return self._overlays["crosshair"]

    @property
    def hover(self) -> HoverOverlay:
        """Hover readout overlay (hidden by default)."""
        return self._overlays["hover"]

    def _pixel_mapper(self) -> PixelMapper | None:
        """Map data coordinates to canvas pixels, or None before the canvas has a size."""
        height, width = self.canvas.size
        xmin, xmax, ymin, ymax = self.camera.rect
        if width <= 0 or height <= 0 or xmax <= xmin or ymax <= ymin:
            return None
        axis = self.axis
        return PixelMapper(
            (xmin, xmax, ymin, ymax), (width, height), axis.x_scale, axis.y_scale, axis.x_power, axis.y_power
        )

    def hover_info(self, x: float, y: float) -> HoverInfo | None:
        """Describe the data point under the data position (``x``, ``y``), or None when no layer has one.

        Every visible plot layer reports its point under the cursor; the one vertically closest to the cursor on
        screen is the primary point, and the others are listed as rows.
        """
        mapper = self._pixel_mapper()
        if mapper is None:
            return None
        hits = [
            point
            for layer in self.layers
            if layer.visible
            and isinstance(layer, np_layers.base.LayerMixin)
            and (point := layer._get_hover_point(x, y, mapper)) is not None
        ]
        if not hits:
            return None
        _, cursor_y = mapper.to_pixels(x, y)
        _, hit_ys = mapper.to_pixels([hit.x for hit in hits], [hit.y for hit in hits])
        distance = np.abs(np.asarray(hit_ys) - cursor_y)
        distance[~np.isfinite(distance)] = np.inf
        primary = hits[int(np.argmin(distance))]
        rows = tuple((hit.label, hit.y) for hit in hits if hit is not primary)
        return HoverInfo(
            primary.x, primary.y, primary.index, primary.label, str(self.axis.x_label), str(self.axis.y_label), rows
        )

    def _update_hover(self, _event: Any = None) -> None:
        """Move the crosshair and update the hover readout for the cursor position."""
        crosshair, hover = self.crosshair, self.hover
        if not self.mouse_over_canvas or not (crosshair.visible or hover.visible):
            crosshair.point, hover.text = None, ""
            return
        y, x = (float(value) for value in self.cursor.position[-2:])
        if self._cursor_panel in ("top", "right"):
            # a marginal shares only one axis with the main panel; its other coordinate is in its own units
            hover.text = ""
            crosshair.point = (x, np.nan) if self._cursor_panel == "top" else (np.nan, y)
            return
        snap = hover.visible or crosshair.snap_to_data
        info = self.hover_info(x, y) if snap else None
        if hover.visible:
            hover.text = "" if info is None else (hover.formatter or HoverInfo.format)(info)
        # without data under the cursor, the crosshair follows the cursor freely
        crosshair.point = (info.x, info.y) if info is not None else (x, y)

    @property
    def _brush_circle_overlay(self):
        return self._overlays["brush_circle"]

    @property
    def legend_visible(self) -> bool:
        """Whether the default legend overlay is visible."""
        return self.legend.visible

    def set_legend_visible(self, visible: bool) -> None:
        """Set default legend visibility."""
        self.legend.visible = visible

    def set_legend(
        self,
        entries: LegendInput,
        *,
        visible: bool = True,
        position: str = "top_right",
        text_color: LegendColorLike = None,
        font_size: float | None = None,
        marker_size: float = 10.0,
        row_spacing: float = 9.0,
        padding: float = 6.0,
        background_color: LegendColorLike = None,
        border_color: LegendColorLike = None,
        border_width: float = 1.0,
        title: str = "",
        ncols: int = 1,
        outside: bool = False,
    ) -> LegendOverlay:
        """Configure the default canvas legend from explicit entries."""
        overlay = self.legend
        overlay.source_layer = None
        overlay.sync_with_source = False
        overlay.visible = visible
        overlay.position = position
        overlay.text_color = text_color
        overlay.font_size = font_size
        overlay.marker_size = marker_size
        overlay.row_spacing = row_spacing
        overlay.padding = padding
        overlay.background_color = background_color
        overlay.border_color = border_color
        overlay.border_width = border_width
        overlay.title = title
        overlay.ncols = ncols
        overlay.outside = outside
        overlay.set_entries(entries)
        self._refresh_legend_source_connections()
        return overlay

    def set_legend_from_layers(
        self,
        *,
        sync: bool = True,
        visible: bool = True,
        position: str = "top_right",
        text_color: LegendColorLike = None,
        font_size: float | None = None,
        marker_size: float = 10.0,
        row_spacing: float = 9.0,
        padding: float = 6.0,
        background_color: LegendColorLike = None,
        border_color: LegendColorLike = None,
        border_width: float = 1.0,
        title: str = "",
        ncols: int = 1,
        outside: bool = False,
    ) -> LegendOverlay:
        """Configure the default legend from visible plot layers."""
        overlay = self.set_legend(
            legend_entries_from_layers(self.layers),
            visible=visible,
            position=position,
            text_color=text_color,
            font_size=font_size,
            marker_size=marker_size,
            row_spacing=row_spacing,
            padding=padding,
            background_color=background_color,
            border_color=border_color,
            border_width=border_width,
            title=title,
            ncols=ncols,
            outside=outside,
        )
        overlay.sync_with_source = sync
        self._refresh_legend_source_connections()
        return overlay

    def refresh_legend_from_layers(self) -> LegendOverlay:
        """Refresh the default legend without changing its visual style."""
        self.legend.set_entries(legend_entries_from_layers(self.layers))
        return self.legend

    def set_legend_from_points(
        self,
        layer: str | n_layers.Points,
        *,
        label_property: str = "label",
        color_source: str = "face",
        marker_source: str = "symbol",
        group_by_style: bool = True,
        sync: bool = False,
        visible: bool = True,
        **style: Any,
    ) -> LegendOverlay:
        """Configure the default legend from categorized Points data."""
        points = self.layers[layer] if isinstance(layer, str) else layer
        if not isinstance(points, n_layers.Points):
            raise TypeError("Legend source layer must be a Points layer.")
        overlay = self.set_legend(
            legend_entries_from_points(
                points,
                label_property=label_property,
                color_source=color_source,
                marker_source=marker_source,
                group_by_style=group_by_style,
            ),
            visible=visible,
            **style,
        )
        overlay.source_layer = points.name
        overlay.label_property = label_property
        overlay.color_source = color_source
        overlay.marker_source = marker_source
        overlay.group_by_style = group_by_style
        overlay.sync_with_source = sync
        self._refresh_legend_source_connections()
        return overlay

    def refresh_legend_from_source(self) -> LegendOverlay:
        """Refresh a Points-derived legend from its configured source."""
        overlay = self.legend
        if overlay.source_layer is None:
            return self.refresh_legend_from_layers()
        with suppress(KeyError):
            layer = self.layers[overlay.source_layer]
            if isinstance(layer, n_layers.Points):
                overlay.set_entries(
                    legend_entries_from_points(
                        layer,
                        label_property=overlay.label_property,
                        color_source=overlay.color_source,
                        marker_source=overlay.marker_source,
                        group_by_style=overlay.group_by_style,
                    )
                )
        return overlay

    def set_legend_auto_sync(self, enabled: bool = True) -> LegendOverlay:
        """Enable or disable automatic legend source updates."""
        self.legend.sync_with_source = enabled
        if enabled:
            self.refresh_legend_from_source()
        self._refresh_legend_source_connections()
        return self.legend

    def clear_legend(self) -> None:
        """Clear and hide the default legend without removing its canvas visual."""
        self.legend.set_entries(None)
        self.legend.visible = False
        self.legend.source_layer = None
        self.legend.sync_with_source = False
        self._refresh_legend_source_connections()

    def _on_legend_layers_change(self, _event: Event | None = None) -> None:
        """Refresh automatic legend state after layer collection changes."""
        self._refresh_legend_source_connections()
        if self.legend.sync_with_source:
            self.refresh_legend_from_source()

    def _disconnect_legend_source_layer(self, layer: n_layers.Layer) -> None:
        for event_name in LEGEND_LAYER_EVENTS:
            with suppress(AttributeError, KeyError, ValueError):
                getattr(layer.events, event_name).disconnect(self._on_legend_source_change)

    def _connect_legend_source_layer(self, layer: n_layers.Layer) -> None:
        for event_name in LEGEND_LAYER_EVENTS:
            with suppress(AttributeError, KeyError):
                getattr(layer.events, event_name).connect(self._on_legend_source_change)

    def _refresh_legend_source_connections(self, _event: Event | None = None) -> None:
        """Reconnect live legend source listeners."""
        for layer in self._legend_source_layers:
            self._disconnect_legend_source_layer(layer)
        self._legend_source_layers = []
        if not self.legend.sync_with_source:
            return
        if self.legend.source_layer is not None:
            with suppress(KeyError):
                layer = self.layers[self.legend.source_layer]
                if isinstance(layer, n_layers.Points):
                    self._legend_source_layers.append(layer)
        else:
            self._legend_source_layers.extend(self.layers)
        for layer in self._legend_source_layers:
            self._connect_legend_source_layer(layer)

    def _on_legend_source_change(self, event: Event | None = None) -> None:
        """Refresh the synced legend from its configured source."""
        if self.legend.sync_with_source:
            if (
                event is not None
                and event.type == "name"
                and self.legend.source_layer is not None
                and isinstance(event.source, n_layers.Points)
            ):
                self.legend.source_layer = event.source.name
            self.refresh_legend_from_source()

    @field_validator("theme")
    @classmethod
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

    def save_session(self, path: str | Path) -> None:
        """Save the current plot settings and layer data to a portable session archive."""
        from napari_plot._session import save_session

        save_session(self, path)

    def load_session(self, path: str | Path) -> list[n_layers.Layer]:
        """Replace the current plot with a saved session and return the restored layers."""
        from napari_plot._session import load_session

        return load_session(self, path)

    def export_csv(self, layer: n_layers.Layer | str, path: str | Path) -> None:
        """Write the source data of a layer (or named layer) to a CSV file."""
        from napari_plot._data_io import export_csv

        export_csv(self.layers[layer] if isinstance(layer, str) else layer, path)

    def open(
        self,
        path: str | Path | Sequence[str | Path],
        *,
        stack: bool | list[list[str]] = False,
        plugin: str | None = None,
        layer_type: str | None = None,
        **kwargs: Any,
    ) -> list[n_layers.Layer]:
        """Open saved sessions, two-column CSV plots, or files supported by napari readers."""
        from napari_plot._data_io import open_paths

        return open_paths(self, path, stack=stack, plugin=plugin, layer_type=layer_type, **kwargs)

    def model_dump(self, **kwargs) -> dict:
        """Convert to a dictionary."""
        # Manually exclude the layer list and active layer which cannot be serialized at this point
        # and mouse and keybindings don't belong on model
        # https://github.com/samuelcolvin/pydantic/pull/2231
        # https://github.com/samuelcolvin/pydantic/issues/660#issuecomment-642211017
        exclude = kwargs.pop("exclude", set())
        exclude = exclude.union(EXCLUDE_DICT)
        return super().model_dump(exclude=exclude, **kwargs)

    def __hash__(self):
        return id(self)

    def __str__(self):
        """Simple string representation"""
        return f"napari_plot.Viewer: {self.title}"

    def _on_layer_list_event(self, event: Event) -> None:
        """Update the data extent for layer-list events, and layer events re-emitted by it, that can change it.

        Data and transform changes are handled by `_on_layers_change`; appearance changes (thumbnail, colour, ...)
        never move the data, and recomputing the extent for each of them made frequent data updates slow.
        """
        if event.type not in _EXTENT_NEUTRAL_EVENTS:
            self._on_update_extent(event)

    def _on_update_extent(self, _event=None):
        """Update data extent when there has been a change to the list of layers"""
        fitted = self.camera.rect
        previous = self.camera.get_effective_extent()
        extent = self._get_rect_extent()
        # Private extent that is always the same as extent of the data. It is essential that whenever extent is set
        # on the camera, the value of `_extent` is also set as it will be used as a value for resetting axis values
        # if e.g. user uses the `camera.x_range` or `camera.set_x_range`.
        self.camera._extent = (
            self._get_rect_extent(use_camera_range=False)
            if self.camera.x_range is not None or self.camera.y_range is not None
            else extent
        )
        # update extent - must be done after `_extent`
        self.camera.extent = extent
        if self.autoscale and self.layers:
            xlim = extent[:2] if np.allclose(fitted[:2], previous[:2], rtol=1e-12, atol=1e-10) else fitted[:2]
            ylim = extent[2:] if np.allclose(fitted[2:], previous[2:], rtol=1e-12, atol=1e-10) else fitted[2:]
            self.camera.set_rect(*xlim, *ylim)

    def _on_autoscale_changed(self, _event: Event | None = None) -> None:
        if self.autoscale and self.layers:
            self.reset_view()

    @field_validator("margins")
    @classmethod
    def _validate_margins(cls, value: tuple[float, float]) -> tuple[float, float]:
        if any(not np.isfinite(margin) or margin < 0 for margin in value):
            raise ValueError("Data margins must be finite, nonnegative fractions.")
        return value

    @property
    def xlim(self) -> tuple[float, float]:
        """Current x limits in data coordinates and display order."""
        low, high = self.camera.rect[:2]
        return (high, low) if self.axis.x_inverted else (low, high)

    @xlim.setter
    def xlim(self, value: tuple[float, float] | None) -> None:
        self._set_axis_limits("x", value)

    @property
    def ylim(self) -> tuple[float, float]:
        """Current y limits in data coordinates and display order."""
        low, high = self.camera.rect[2:]
        return (high, low) if self.axis.y_inverted else (low, high)

    @ylim.setter
    def ylim(self, value: tuple[float, float] | None) -> None:
        self._set_axis_limits("y", value)

    def _set_axis_limits(self, axis: Literal["x", "y"], value: tuple[float, float] | None) -> None:
        """Apply one axis's data limits; descending limits invert the displayed axis."""
        index = 0 if axis == "x" else 2
        if value is None:
            limits = self._get_rect_extent()[index : index + 2]
        else:
            first, last = map(float, value)
            if not np.isfinite((first, last)).all() or first == last:
                raise ValueError("Axis limits must be two distinct finite values.")
            lower, upper = sorted((first, last))
            if getattr(self.axis, f"{axis}_scale") is AxisScale.LOG and lower <= 0:
                raise ValueError("Logarithmic axis limits must be positive.")
            setattr(self.axis, f"{axis}_inverted", first > last)
            limits = (lower, upper)
        rect = self.camera.rect
        self.camera.rect = (*rect[:index], *limits, *rect[index + 2 :])

    def clear_canvas(self):
        """Remove all layers from the canvas"""
        self.layers.remove_all()
        self.events.clear_canvas()

    def reset_plot(self) -> None:
        """Remove all layers and reset what plots leave behind.

        This covers categorical axes (incl. tick rotation and thinning), log scales, fixed ranges, legend, colorbar and
        text overlays.
        """
        self.canvas.grid.update(
            {"joint": False, "joint_top_label": "", "joint_right_label": "", "joint_hidden_labels": ()}
        )
        self.clear_canvas()
        self.camera.x_range = None
        self.camera.y_range = None
        self.axis.x_categories = None
        self.axis.y_categories = None
        self.axis.x_tick_rotation = 0.0
        self.axis.x_thin_categories = True
        self.axis.y_thin_categories = True
        self.axis.x_scale = "linear"
        self.axis.y_scale = "linear"
        self.axis.x_inverted = False
        self.axis.y_inverted = False
        self.canvas.grid.cells = ()
        self.clear_legend()
        self.clear_colorbar()
        for cell in self._cell_colorbars:
            self.clear_colorbar(cell=cell)
        self.remove_text_overlays()

    def add_text_overlay(
        self,
        text: str,
        position: str = "top_left",
        name: str | None = None,
        **kwargs: Any,
    ) -> TextOverlay:
        """Show `text` at a corner or edge of the plot area (e.g. a statistics box), unaffected by zooming.

        Unlike ``text_overlay`` (used as the plot title), any number of these can be added. ``position`` is a canvas
        position such as ``top_left`` or ``bottom_right``; other keyword arguments (``color``, ``font_size``, ``box``,
        ...) are passed to napari's ``TextOverlay``. Adding text with the name of an earlier one replaces it.
        """
        name = name or f"text {len(self._text_overlay_names)}"
        key = f"annotation:{name}"
        overlay = TextOverlay(text=text, position=position, visible=True, **kwargs)
        if key in self._overlays:
            del self._overlays[key]
        else:
            self._text_overlay_names.append(key)
        self._overlays[key] = overlay
        return overlay

    def remove_text_overlays(self) -> None:
        """Remove every text added with `add_text_overlay`."""
        for key in self._text_overlay_names:
            with suppress(KeyError):
                del self._overlays[key]
        self._text_overlay_names.clear()

    def colorbar_for_cell(self, row: int, col: int) -> ColorBar:
        """Return the independent colorbar settings for the given grid cell."""
        if row < 0 or col < 0:
            raise ValueError("Colorbar cell coordinates must be non-negative.")
        cell = (row, col)
        if cell not in self._cell_colorbars:
            self._cell_colorbars[cell] = ColorBar()
            self.events.colorbars_change()
        return self._cell_colorbars[cell]

    def set_colorbar_from_layer(
        self,
        layer: n_layers.Layer | str,
        label: str = "",
        *,
        cell: tuple[int, int] | None = None,
        position: Literal["right", "bottom"] | None = None,
        orientation: Literal["vertical", "horizontal"] | None = None,
        norm: Literal["linear", "log"] | None = None,
    ) -> ColorBar:
        """Show the continuous color scale of an image or scatter layer, optionally in a grid cell."""
        if isinstance(layer, str):
            layer = self.layers[layer]
        emitters = self._colorbar_events(layer)
        if not emitters:
            raise TypeError("Colorbars require a layer with an intensity or face colormap.")
        colorbar = self.colorbar if cell is None else self.colorbar_for_cell(*cell)
        if position is not None:
            colorbar.position = position
        if orientation is not None:
            colorbar.orientation = orientation
        if norm is not None:
            colorbar.norm = norm
        self._disconnect_colorbar_source(cell)
        if layer not in self._colorbar_sources.values():
            for emitter in emitters:
                emitter.connect(self._sync_colorbar)
        self._colorbar_sources[cell] = layer
        colorbar.label = label
        self._sync_colorbar()
        colorbar.visible = True
        return colorbar

    def clear_colorbar(self, *, cell: tuple[int, int] | None = None) -> None:
        """Hide the global or per-cell colorbar and disconnect its source."""
        self._disconnect_colorbar_source(cell)
        colorbar = self.colorbar if cell is None else self._cell_colorbars.get(cell)
        if colorbar is not None:
            colorbar.visible = False

    @staticmethod
    def _colorbar_events(layer: n_layers.Layer) -> tuple[EventEmitter, ...]:
        if isinstance(layer, n_layers.Points):
            return layer._face.events.continuous_colormap, layer._face.events.contrast_limits
        if not hasattr(layer, "contrast_limits") or not hasattr(layer, "colormap"):
            return ()
        return tuple(
            getattr(layer.events, name)
            for name in ("colormap", "contrast_limits", "gamma")
            if hasattr(layer.events, name)
        )

    def _disconnect_colorbar_source(self, cell: tuple[int, int] | None) -> None:
        layer = self._colorbar_sources.pop(cell, None)
        if layer is not None and layer not in self._colorbar_sources.values():
            for emitter in self._colorbar_events(layer):
                emitter.disconnect(self._sync_colorbar)

    def _sync_colorbar(self, _event: Event | None = None) -> None:
        """Copy the colormap and contrast limits of the source layer to the colorbar."""
        for cell, layer in self._colorbar_sources.items():
            colorbar = self.colorbar if cell is None else self._cell_colorbars[cell]
            if isinstance(layer, n_layers.Points):
                colorbar.colormap = layer.face_colormap
                limits = layer.face_contrast_limits or (0.0, 1.0)
            else:
                colorbar.colormap = layer.colormap
                limits = layer.contrast_limits
            colorbar.contrast_limits = (float(limits[0]), float(limits[1]))
            colorbar.gamma = getattr(layer, "gamma", 1.0)

    @property
    def _sliced_extent_world(self) -> np.ndarray:
        """Return plot layer bounds as two world-coordinate (y, x) pairs."""
        return self.layers.extent.world[:, (0, 1)]

    @property
    def _sliced_extent_world_augmented(self) -> np.ndarray:
        """Return plot bounds padded by half a sample step where applicable."""
        # if not layers are present, assume image-like with dimensions of size 512
        if len(self.layers) == 0:
            return np.vstack([np.full(self.dims.ndim, -0.5), np.full(self.dims.ndim, 511.5)])
        return self.layers._extent_world_augmented[:, self.dims.displayed]

    def _get_rect_extent(
        self,
        *,
        layers: Sequence[n_layers.Layer] | None = None,
        cell: PlotGridCell | None = None,
        margin: float | tuple[float, float] | None = None,
        use_camera_range: bool = True,
    ) -> tuple[float, float, float, float]:
        """Get data extent, including image pixel edges and room for line widths and marker sizes."""
        grid = self.canvas.grid
        if layers is None and grid.enabled and grid.joint:
            visible = [
                (layer, joint_panel(layer, top=grid.joint_top, right=grid.joint_right))
                for layer in self.layers
                if layer.visible
            ]
            x_layers = [layer for layer, panel in visible if panel != "right"]
            y_layers = [layer for layer, panel in visible if panel != "top"]
            x_extent = self._get_rect_extent(layers=x_layers, margin=margin, use_camera_range=use_camera_range)
            y_extent = self._get_rect_extent(layers=y_layers, margin=margin, use_camera_range=use_camera_range)
            return (*x_extent[:2], *y_extent[2:])
        if layers is None:
            extent = self._sliced_extent_world
        elif len(layers):
            extent = self.layers.get_extent(layers).world[:, -2:]
        else:
            extent = np.array([[-0.5, -0.5], [0.5, 0.5]])
        layers = self.layers if layers is None else layers
        ymin, ymax = get_min_max(extent[:, 0])
        xmin, xmax = get_min_max(extent[:, 1])
        for layer in layers:
            # image pixels are centered on their coordinates, so the rendered image extends half a pixel further
            if layer.visible and isinstance(layer, (n_layers.Image, n_layers.Labels)):
                augmented = layer._extent_world_augmented[:, -2:]
                ymin, ymax = min(ymin, augmented[0, 0]), max(ymax, augmented[1, 0])
                xmin, xmax = min(xmin, augmented[0, 1]), max(xmax, augmented[1, 1])
        pad_px = self._extent_padding_px(layers)
        height, width = self._canvas_size
        if margin is None:
            margin = self.margins
        if np.isscalar(margin):
            margin = (margin, margin)
        rect = []
        for name, bounds, size, padding in zip(
            ("x", "y"), ((xmin, xmax), (ymin, ymax)), (width, height), margin, strict=True
        ):
            scale = cell.axis_scale(name, self.axis) if cell is not None else getattr(self.axis, f"{name}_scale")
            lower, upper = bounds
            if scale in (AxisScale.LINEAR, AxisScale.DATETIME):
                lower, upper = _pad_by_pixels(lower, upper, pad_px, size)
            custom_range = getattr(self.camera, f"{name}_range") if use_camera_range else None
            if cell is not None:
                custom_range = getattr(cell, f"{name}lim") or custom_range
            if custom_range is not None:
                lower, upper = sorted(custom_range)
            lower, upper = self._sanitize_log_extent(lower, upper, name, scale=scale, layers=layers)
            if custom_range is None and padding and scale is not AxisScale.CATEGORICAL:
                power = getattr(self.axis, f"{name}_power")
                transformed = transform_axis_values(np.asarray([lower, upper]), scale, power=power)
                pad = (transformed[1] - transformed[0]) * padding
                lower, upper = transform_axis_values(transformed + (-pad, pad), scale, power=power, inverse=True)
            rect.extend((float(lower), float(upper)))
        return rect[0], rect[1], rect[2], rect[3]

    def _extent_padding_px(self, layers: Sequence[n_layers.Layer]) -> float:
        """Return the screen-pixel padding needed so lines and pixel-sized markers at the data edge are not clipped."""
        pad = 0.0
        for layer in layers:
            if not layer.visible:
                continue
            if isinstance(layer, (np_layers.Line, np_layers.MultiLine)):
                pad = max(pad, float(layer.width) / 2)
            elif isinstance(layer, np_layers.Scatter) and not layer.scaling and len(layer.size):
                border = float(np.max(layer.border_width)) if not layer.border_width_is_relative else 0.0
                pad = max(pad, float(np.max(layer.size)) / 2 + border)
        return pad

    def _sanitize_log_extent(
        self,
        lower: float,
        upper: float,
        axis: Literal["x", "y"],
        *,
        scale: AxisScale | None = None,
        layers: Sequence[n_layers.Layer] | None = None,
    ) -> tuple[float, float]:
        """Return positive limits for a logarithmic axis."""
        if scale is None:
            scale = self.axis.x_scale if axis == "x" else self.axis.y_scale
        if scale is not AxisScale.LOG:
            return lower, upper

        if lower <= 0:
            lower = self._get_positive_axis_min(axis, upper, layers=layers)
        upper = upper if upper > lower else lower * 10.0
        return lower, upper

    def _get_positive_axis_min(
        self,
        axis: Literal["x", "y"],
        fallback_max: float,
        *,
        layers: Sequence[n_layers.Layer] | None = None,
    ) -> float:
        """Return the smallest positive layer coordinate on an axis."""
        candidates: list[float] = []
        world_axis = 1 if axis == "x" else 0
        for layer in self.layers if layers is None else layers:
            if not layer.visible:
                continue
            values = getattr(layer, axis, None)
            if values is None and hasattr(layer, "_data_view"):
                values = getattr(layer._data_view, f"{axis}s", None)
            if values is not None:
                arrays = values if isinstance(values, (list, tuple)) else [values]
                for value in arrays:
                    array = np.asarray(value, dtype=float)
                    positive = array[np.isfinite(array) & (array > 0)]
                    if positive.size:
                        candidates.append(float(np.min(positive)))
                continue

            layer_extent = layer.extent.world[:, world_axis]
            if np.isfinite(layer_extent[0]) and layer_extent[0] > 0:
                candidates.append(float(layer_extent[0]))

        if candidates:
            return min(candidates)
        if np.isfinite(fallback_max) and fallback_max > 0:
            return float(fallback_max) * 1e-6
        return 1.0

    def _get_y_range_extent_for_x(
        self,
        xmin: float,
        xmax: float,
        ymin: float | None = 0,
        auto_scale: bool = True,
        y_multiplier: float = 1.0,
    ) -> tuple[float, float]:
        """Calculate y-axis range for the specified x-axis range.

        When ``auto_scale`` is enabled, the range is fitted to the data of layers that can report their y-axis extent
        within an x-axis window (e.g. line or centroids). If no such layer exists (e.g. scatter only), the current
        y-axis view is kept. ``ymin`` acts as a baseline that is always included and never padded, while the data ends
        are padded by ``y_multiplier - 1`` of the range.
        """
        if not auto_scale:
            _, _, real_ymin, real_ymax = self._get_rect_extent()
            return real_ymin, real_ymax * y_multiplier

        layers = self.layers
        grid = self.canvas.grid
        if grid.enabled and grid.joint:
            layers = [
                layer for layer in layers if joint_panel(layer, top=grid.joint_top, right=grid.joint_right) == "joint"
            ]
        region_min, region_max = get_layers_x_region_extent(xmin, xmax, layers)
        if region_min is None:
            _, _, current_ymin, current_ymax = self.camera.rect
            return current_ymin, current_ymax

        lower, upper = get_min_max([region_min, region_max] if ymin is None else [region_min, region_max, ymin])
        padding = (upper - lower) * (y_multiplier - 1)
        if ymin is None or lower < ymin:
            lower -= padding
        if ymin is None or upper > ymin:
            upper += padding
        return lower, upper

    def _get_value_range_in_region(
        self, layers: Sequence[n_layers.Layer], axis: int, lo: float, hi: float, multiplier: float = 1.05
    ) -> tuple[float, float] | None:
        """Value range of ``layers`` over the data whose ``axis`` (0 = x, 1 = y) coordinate is in ``[lo, hi]``.

        Used to fit the value axis of a joint marginal to what is visible along its shared axis. Zero is always
        included as a baseline and the data end(s) away from it are padded by ``multiplier - 1`` of the range.
        Returns None when no layer has data in the range (or the data is flat at zero).
        """
        region_min, region_max = get_layers_region_extent(axis, lo, hi, layers)
        if region_min is None:
            return None
        lower, upper = min(region_min, 0.0), max(region_max, 0.0)
        if upper <= lower:
            return None
        padding = (upper - lower) * (multiplier - 1)
        return (lower - padding if lower < 0 else lower), (upper + padding if upper > 0 else upper)

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
        xmin, xmax = self._sanitize_log_extent(xmin, xmax, "x")
        ymin, ymax = self._sanitize_log_extent(ymin, ymax, "y")
        self.camera.set_rect(xmin, xmax, ymin, ymax)

    def reset_view(
        self,
        _event: Event | None = None,
        *,
        margin: float | tuple[float, float] | None = None,
        use_camera_range: bool = True,
    ) -> None:
        """Fit the view to the data with optional fractional margins and camera range overrides."""
        xmin, xmax, ymin, ymax = self._get_rect_extent(margin=margin, use_camera_range=use_camera_range)
        self.camera.set_rect(xmin, xmax, ymin, ymax)
        self.events.reset_view()

    def reset_x_view(self, _event=None):
        """Reset the camera view, but only in the y-axis dimension"""
        xmin, xmax, _, _ = self._get_rect_extent()
        _, _, ymin, ymax = self.camera.rect
        self.camera.set_rect(xmin, xmax, ymin, ymax)

    def set_y_view(self, ymin: float, ymax: float):
        """Set view on specified y-axis"""
        xmin, xmax, _, _ = self._get_rect_extent()
        ymin, ymax = self._sanitize_log_extent(ymin, ymax, "y")
        self.camera.set_rect(xmin, xmax, ymin, ymax)

    def reset_y_view(self, _event=None):
        """Reset the camera view, but only in the y-axis dimension"""
        _, _, ymin, ymax = self._get_rect_extent()
        xmin, xmax, _, _ = self.camera.rect
        self.camera.set_rect(xmin, xmax, ymin, ymax)

    def reset_current_y_view(self, _event=None):
        """Reset y-axis for current selection."""
        xmin, xmax, _, _ = self.camera.rect
        self.set_x_view(xmin, xmax)

    def update_extents(self, _event=None):
        """Reset y-axis for current selection."""
        self.camera.extent = self._get_rect_extent()

    def _on_update_tool(self, event):
        """Update drag method based on currently active tool."""
        from napari_plot.components.dragtool import BOX_ZOOM_TOOLS, SELECT_TOOLS, DragMode
        from napari_plot.components.tools import Shape

        _discard_active_generators(self, "drag")
        if self.drag_tool.tool is not None:
            self.drag_tool.tool.visible = False

        # if self.drag_tool.tool not in BOX_ZOOM_TOOLS:
        for callback_func in [
            box_zoom_box,
            box_zoom_vert,
            box_zoom_horz,
            box_zoom_auto,
            box_zoom_auto_trigger,
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
        # make sure flag set by `auto_trigger` does not leak into other tools
        self.drag_tool.selection_active = False
        # zoom tools
        if self.drag_tool.active in BOX_ZOOM_TOOLS:
            tool = self.drag_tool.tool if isinstance(self.drag_tool.tool, BoxTool) else self.drag_tool._box
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
                self.mouse_drag_callbacks.append(box_zoom_auto)
            elif tool and self.drag_tool.active == DragMode.AUTO_TRIGGER:
                tool.shape = Shape.BOX
                self.mouse_drag_callbacks.append(box_zoom_auto_trigger)
        # selection tools
        elif self.drag_tool.active in SELECT_TOOLS:
            if self.drag_tool.active == DragMode.POLYGON:
                tool = self.drag_tool.tool if isinstance(self.drag_tool.tool, PolygonTool) else self.drag_tool._polygon
                self.mouse_drag_callbacks.append(polygon_select)
            elif self.drag_tool.active == DragMode.LASSO:
                tool = self.drag_tool.tool if isinstance(self.drag_tool.tool, PolygonTool) else self.drag_tool._polygon
                self.mouse_drag_callbacks.append(lasso_select)
            elif self.drag_tool.active == DragMode.BOX_SELECT:
                tool = self.drag_tool.tool if isinstance(self.drag_tool.tool, BoxTool) else self.drag_tool._box
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

    def _select_data(self, vertices: np.ndarray, *, cell: tuple[int, int] | None = None) -> None:
        """Replace the selected indices in the visible, selected plot layers."""
        valid = len(vertices) >= 3 and np.isfinite(vertices).all()
        if valid:
            span = np.ptp(vertices, axis=0)
            valid = np.all(span > 0) and np.linalg.matrix_rank((vertices[1:] - vertices[0]) / span) == 2
        layers: Sequence[n_layers.Layer] = self.layers
        if cell is not None and self.canvas.grid.enabled:
            layers = [
                self.layers[index]
                for position, indices in self.canvas.grid.iter_viewboxes(self.layers)
                if position == cell
                for index in indices
            ]
        selection: dict[n_layers.Layer, set[int]] = {}
        for layer in layers:
            if layer not in self.layers.selection or not layer.visible:
                continue
            if not isinstance(
                layer, (np_layers.Scatter, np_layers.Line, np_layers.MultiLine, np_layers.Bar, np_layers.Centroids)
            ):
                continue
            indices: set[int] = set()
            if valid:
                layer_vertices = np.asarray([layer.world_to_data(vertex) for vertex in vertices])
                indices = set(np.flatnonzero(layer._selection_mask(layer_vertices)).tolist())
            layer.selected_data = indices
            selection[layer] = indices.copy()
        self.events.selection(value=selection, vertices=vertices.copy())

    def _on_joint_metadata_change(self, _event: Event | None = None) -> None:
        if self.canvas.grid.joint:
            self._on_update_extent()
            self.events.layers_change()

    def _on_layers_change(self, _event=None):
        if getattr(_event, "type", None) in _LAYER_GEOMETRY_EVENTS:
            # keep the cursor (and crosshair) where it is, e.g. while a layer is updated during a pan
            self._update_hover()
            self._update_axis_labels()
            self._on_update_extent()
            # only the plot cell of this layer has new data limits
            self.events.layers_change(layer=_event.source)
            return
        self.cursor.position = (0,) * 2
        self._update_axis_labels()
        self.events.layers_change()  # TODO: remove

    def _on_axis_label_changed(self, event: Event) -> None:
        if not self._setting_axis_labels:
            self._explicit_axis_labels.add(event.type)

    def _update_axis_labels(self, _event: Event | None = None) -> None:
        """Inherit layer metadata while preserving explicit plot axis labels."""
        labels = list(map(str, range(-self.dims.ndim, 0)))
        for layer in sorted(self.layers, key=lambda item: -item.ndim):
            if not layer._has_default_axis_labels():
                count = min(self.dims.ndim, layer.ndim)
                labels[-count:] = layer.axis_labels[-count:]
                break
        self.dims.axis_labels = tuple(labels)
        defaults = {"x_label": "X-label", "y_label": "Y-label"}
        self._setting_axis_labels = True
        try:
            for attribute, label in zip(("y_label", "x_label"), labels[-2:], strict=True):
                if attribute not in self._explicit_axis_labels:
                    default_label = label in tuple(map(str, range(-self.dims.ndim, 0)))
                    setattr(self.axis, attribute, defaults[attribute] if default_label else label)
        finally:
            self._setting_axis_labels = False

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
    ) -> tuple[str | dict, str] | None:
        if not self.mouse_over_canvas:
            return None
        active = self.layers.selection.active
        if active is not None and active._slicing_state._loaded:
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

            # plot coordinates read as x/y rather than napari's world-order [y x]
            status["coords"] = coords = format_coordinates(*self.cursor.position[-2:][::-1])
            status["coordinates"] = f"{coords}: {status['value']}" if status.get("value") else coords
            return status, tooltip_text
        if active is None:
            return format_coordinates(*self.cursor.position[-2:][::-1]), ""
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
        layer.events.axis_labels.connect(self._update_axis_labels)
        layer.events.scale.connect(self._on_layers_change)
        layer.events.translate.connect(self._on_layers_change)
        layer.events.rotate.connect(self._on_layers_change)
        layer.events.shear.connect(self._on_layers_change)
        layer.events.affine.connect(self._on_layers_change)
        layer.events.name.connect(self.layers._update_name)
        layer.events.reload.connect(self._on_layer_reload)
        layer.events.visible.connect(self._on_update_extent)
        layer.events.metadata.connect(self._on_joint_metadata_change)
        if hasattr(layer.events, "mode"):
            layer.events.mode.connect(self._on_layer_mode_change)
        self._layer_help_from_mode(layer)

        # Update dims and grid model
        self._on_layers_change(None)
        # Slice current layer based on dims
        self._update_layers(layers=[layer])

        if len(self.layers) == 1:
            if self.autoscale:
                self.reset_view()
            self.dims._go_to_center_step()

    @staticmethod
    def _layer_help_from_mode(layer: n_layers.Layer):
        """Update layer help text base on layer mode."""
        from napari.layers.image._image_key_bindings import image_fun_to_mode
        from napari.layers.labels._labels_key_bindings import labels_fun_to_mode
        from napari.layers.points._points_key_bindings import points_fun_to_mode
        from napari.layers.shapes._shapes_key_bindings import shapes_fun_to_mode
        from napari.layers.vectors._vectors_key_bindings import vectors_fun_to_mode

        from napari_plot.layers.centroids._centroids_key_bindings import centroids_fun_to_mode
        from napari_plot.layers.infline._infline_key_bindings import infline_fun_to_mode
        from napari_plot.layers.line._line_key_bindings import line_fun_to_mode
        from napari_plot.layers.multiline._multiline_key_bindings import multiline_fun_to_mode
        from napari_plot.layers.region._region_key_bindings import region_fun_to_mode
        from napari_plot.layers.scatter._scatter_key_bindings import scatter_fun_to_mode

        # from napari.layers.surface._surface_key_bindings import surface_fun_to_mode
        # from napari.layers.tracks._tracks_key_bindings import tracks_fun_to_mode
        from napari_plot.utils.action_manager import action_manager

        layer_to_func_and_mode: dict[type[n_layers.Layer], list] = {
            n_layers.Points: points_fun_to_mode,
            n_layers.Labels: labels_fun_to_mode,
            n_layers.Shapes: shapes_fun_to_mode,
            n_layers.Image: image_fun_to_mode,
            n_layers.Vectors: vectors_fun_to_mode,
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
        # napari-plot actions keep their shortcuts in their own manager, not in napari's settings
        shortcuts = action_manager._shortcuts

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
        for cell, source in tuple(self._colorbar_sources.items()):
            if source is layer:
                self.clear_colorbar(cell=cell)

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

    def plot(self, x: Any, y: Any | None = None, **kwargs: Any) -> np_layers.Line:
        """Add a line from ``plot(y)`` or ``plot(x, y)`` coordinates."""
        return self.add_line(_plot_data(x, y), **kwargs)

    def scatter(self, x: Any, y: Any | None = None, **kwargs: Any) -> np_layers.Scatter:
        """Add scatter points from ``scatter(y)`` or ``scatter(x, y)`` coordinates."""
        _plot_color(kwargs, "face_color")
        # Scatter follows napari's row/column convention and stores (y, x).
        return self.add_scatter(_plot_data(x, y)[:, ::-1], **kwargs)

    def fill_between(self, x: ArrayLike, y1: ArrayLike, y2: ArrayLike = 0, **kwargs: Any) -> np_layers.Band:
        """Fill between two bounds on a shared x grid. Either bound can be a scalar."""
        _plot_color(kwargs, "fill_color")
        return self.add_band(_band_rows(x, y1, y2), **kwargs)

    def fill_betweenx(self, y: ArrayLike, x1: ArrayLike, x2: ArrayLike = 0, **kwargs: Any) -> np_layers.Band:
        """Fill between two bounds on a shared y grid. Either bound can be a scalar."""
        _plot_color(kwargs, "fill_color")
        return self.add_band(_band_rows(y, x1, x2), orientation="horizontal", **kwargs)

    def errorbar(
        self,
        x: ArrayLike,
        y: ArrayLike,
        *,
        xerr: ArrayLike | None = None,
        yerr: ArrayLike | None = None,
        **kwargs: Any,
    ) -> np_layers.ErrorBar:
        """Draw intervals from scalar, per-point, or (2, N) lower and upper offsets."""
        centers = _plot_data(x, np.asarray(y))
        count = len(centers)
        offsets = []
        for error in (xerr, yerr):
            values = np.asarray(error, dtype=float) if error is not None else np.asarray(np.nan)
            if values.shape not in {(), (count,), (2, count)}:
                raise ValueError("Error offsets must be a scalar, (N,), or (2, N).")
            offsets.append(np.broadcast_to(values, (2, count)).T)
        return self.add_error_bar(np.column_stack((centers, *offsets)), **kwargs)

    def imshow(self, data: Any, **kwargs: Any) -> n_layers.Image | list[n_layers.Image]:
        """Display an image using the standard image-layer API."""
        return self.add_image(data, **kwargs)

    def vbar(
        self, x: ArrayLike, height: ArrayLike | None = None, *, baseline: float | None = None, **kwargs: Any
    ) -> np_layers.Bar:
        """Add vertical bars from values or explicit x positions and heights."""
        _plot_color(kwargs, "fill_color")
        baseline = kwargs.pop("bottom", 0.0) if baseline is None else baseline
        data = np.asarray(x) if height is None else _plot_data(x, height)
        return self.add_bar(data, orientation="vertical", baseline=baseline, **kwargs)

    def hbar(
        self,
        y: ArrayLike,
        length: ArrayLike | None = None,
        *,
        baseline: float | None = None,
        width: ArrayLike | None = None,
        **kwargs: Any,
    ) -> np_layers.Bar:
        """Add horizontal bars. Use `width` for thickness when `length` is provided."""
        _plot_color(kwargs, "fill_color")
        baseline = kwargs.pop("left", 0.0) if baseline is None else baseline
        if length is None and width is not None and np.ndim(width) != 0:
            length, width = width, None  # Previous keyword for explicit lengths.
        data = np.asarray(y) if length is None else _plot_data(y, length)
        if width is not None:
            kwargs["width"] = float(np.asarray(width))
        return self.add_bar(data, orientation="horizontal", baseline=baseline, **kwargs)

    def axhline(self, y: float = 0, **kwargs: Any) -> np_layers.InfLine:
        """Add a horizontal reference line at y."""
        return self.add_inf_line([y], orientation="horizontal", **kwargs)

    def axvline(self, x: float = 0, **kwargs: Any) -> np_layers.InfLine:
        """Add a vertical reference line at x."""
        return self.add_inf_line([x], orientation="vertical", **kwargs)

    def axhspan(self, ymin: float, ymax: float, **kwargs: Any) -> np_layers.Region:
        """Shade a horizontal span between two y coordinates."""
        return self.add_region([(ymin, ymax)], orientation="horizontal", **kwargs)

    def axvspan(self, xmin: float, xmax: float, **kwargs: Any) -> np_layers.Region:
        """Shade a vertical span between two x coordinates."""
        return self.add_region([(xmin, xmax)], orientation="vertical", **kwargs)

    def text(self, x: ArrayLike, y: ArrayLike, text: str | list[str], **kwargs: Any) -> np_layers.Text:
        """Add one label or a sequence of labels at xy coordinates."""
        return self.add_text(_plot_data(np.atleast_1d(x), np.atleast_1d(y)), text=text, **kwargs)

    def annotate(
        self,
        text: str,
        xy: tuple[float, float],
        xytext: tuple[float, float] | None = None,
        *,
        arrow_color: Any = None,
        arrow_width: float = 1.0,
        **kwargs: Any,
    ) -> np_layers.Text:
        """Label a point and draw an arrow from xytext when it differs from xy."""
        target = np.asarray(xy, dtype=float)
        start = target if xytext is None else np.asarray(xytext, dtype=float)
        if start.shape != (2,) or target.shape != (2,) or not np.isfinite([start, target]).all():
            raise ValueError("Annotation positions must be finite (x, y) pairs.")
        label = self.text(*start, text, **kwargs)
        delta = target - start
        if np.any(delta):
            base = target - 0.12 * delta
            wing = 0.05 * np.asarray((-delta[1], delta[0]))
            self.add_line(
                np.vstack((start, target, base + wing, target, base - wing)),
                color=label.color[0] if arrow_color is None else arrow_color,
                width=arrow_width,
                name=f"{label.name} arrow",
                metadata=dict(label.metadata),
                visible=label.visible,
            )
            self.layers.selection.active = label
        return label

    def stem(
        self, x: ArrayLike, y: ArrayLike | None = None, *, baseline: float = 0.0, **kwargs: Any
    ) -> np_layers.Centroids:
        """Draw stems from a shared baseline to y values."""
        values = _plot_data(x, y)
        return self.add_centroids(
            np.column_stack((values[:, 0], np.full(len(values), baseline), values[:, 1])), **kwargs
        )

    def stackplot(self, x: ArrayLike, *ys: ArrayLike, baseline: float = 0.0, **kwargs: Any) -> np_layers.Areas:
        """Fill successive cumulative bands, with one row of values per band."""
        positions = np.asarray(x)
        values = np.atleast_2d(np.asarray(ys[0] if len(ys) == 1 else ys, dtype=float))
        if positions.ndim != 1 or len(positions) < 2 or values.ndim != 2 or values.shape[1] != len(positions):
            raise ValueError("Stackplot needs matching one-dimensional x and y series with at least two points.")
        bounds = baseline + np.vstack((np.zeros(len(positions)), np.cumsum(values, axis=0)))
        _plot_color(kwargs, "fill_color")
        return self.add_areas(
            [np.column_stack((positions, lower, upper)) for lower, upper in pairwise(bounds)],
            **kwargs,
        )

    def hist(
        self,
        values: ArrayLike,
        bins: int | str | ArrayLike = 10,
        *,
        range: tuple[float, float] | None = None,  # noqa: A002
        weights: ArrayLike | None = None,
        density: bool = False,
        baseline: float = 0.0,
        orientation: Literal["vertical", "horizontal"] = "vertical",
        **kwargs: Any,
    ) -> np_layers.Bar:
        """Add a histogram with NumPy binning and support for uneven bin widths."""
        counts, edges = np.histogram(values, bins=bins, range=range, weights=weights, density=density)
        _plot_color(kwargs, "fill_color")
        widths = np.diff(edges)
        centers = edges[:-1] + widths / 2
        data = np.column_stack((centers, baseline + counts, np.full(len(counts), baseline), widths))
        return self.add_bar(data, orientation=orientation, **kwargs)

    def rectangle(self, xy: tuple[float, float], width: float, height: float, **kwargs: Any) -> np_layers.Rectangles:
        """Add a rectangle from its lower-left corner and dimensions."""
        _plot_color(kwargs, "outline_color")
        x, y = xy
        return self.add_rectangles([[x + width / 2, y + height / 2, height, width]], **kwargs)

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
    ) -> n_layers.Image | list[n_layers.Image]:
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
def valid_add_kwargs() -> dict[str, set[str]]:
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
    n_layers.Vectors,
    # napari-plot layers
    np_layers.Areas,
    np_layers.Band,
    np_layers.Bar,
    np_layers.ErrorBar,
    np_layers.Line,
    np_layers.Rectangles,
    np_layers.Scatter,
    np_layers.Region,
    np_layers.InfLine,
    np_layers.Centroids,
    np_layers.MultiLine,
    np_layers.Text,
]:
    if _layer.__module__.startswith("napari_plot."):
        func = _create_custom_add_method(_layer)
    else:
        func = create_add_method(_layer)
    setattr(ViewerModel, func.__name__, func)

for _name in stats.__all__:
    setattr(ViewerModel, _name, _StatsMethod(_name))
