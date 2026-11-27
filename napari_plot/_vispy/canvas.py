"""Line-specific vispy canvas"""

from __future__ import annotations

import typing as ty
from contextlib import contextmanager
from weakref import WeakSet

import numpy as np
from napari._vispy import create_vispy_overlay
from napari._vispy.mouse_event import NapariMouseEvent
from napari._vispy.utils.cursor import QtCursorVisual
from napari._vispy.utils.gl import get_max_texture_sizes
from napari._vispy.utils.qt_font import FontInfo
from napari.components._viewer_constants import CanvasPosition
from napari.components.canvas import Orientation
from napari.components.overlays import CanvasOverlay, Overlay
from napari.settings import get_settings
from napari.utils._proxies import ReadOnlyWrapper
from napari.utils.events import disconnect_events
from napari.utils.interactions import (
    mouse_double_click_callbacks,
    mouse_move_callbacks,
    mouse_press_callbacks,
    mouse_release_callbacks,
    mouse_wheel_callbacks,
)
from qtpy.QtCore import QSize
from superqt.utils import qthrottled
from vispy.scene import Node, SceneCanvas as SceneCanvas_, Widget
from vispy.scene.visuals import VisualNode
from vispy.scene.widgets import Grid
from vispy.util.event import Event

from napari_plot._vispy.camera import VispyCamera
from napari_plot._vispy.overlays.axis import VispyXAxisVisual, VispyYAxisVisual
from napari_plot._vispy.overlays.colorbar import VispyColorBarVisual
from napari_plot._vispy.plot_cell import VispyPlotCell, detach_widget, link_axis
from napari_plot._vispy.tools.drag import VispyDragTool
from napari_plot.components.canvas import PlotGridCell
from napari_plot.components.crosshair import CrosshairOverlay
from napari_plot.components.dragtool import SELECT_TOOLS
from napari_plot.components.legend import LegendOverlay

if ty.TYPE_CHECKING:
    from collections.abc import Iterator

    import numpy.typing as npt
    from napari._vispy.layers.base import VispyBaseLayer
    from napari._vispy.overlays.base import VispyBaseOverlay, VispyCanvasOverlay
    from napari._vispy.overlays.text import VispyLayerNameOverlay
    from napari._vispy.utils.qt_font import QtFontManager
    from napari.layers import Layer
    from napari.utils.key_bindings import KeymapHandler
    from qtpy.QtCore import Qt, pyqtBoundSignal
    from qtpy.QtGui import QCursor, QImage
    from vispy.app.backends._qt import CanvasBackendDesktop
    from vispy.app.canvas import DrawEvent, MouseEvent, ResizeEvent
    from vispy.scene import ViewBox

    from napari_plot.viewer import ViewerModel


# largest mouse movement, in pixels, between a right press and release that still opens the context menu
_CONTEXT_MENU_MAX_MOVE = 4.0


class NapariSceneCanvas(SceneCanvas_):
    """Vispy scene canvas for plot interaction."""

    view, grid, x_axis, y_axis = None, None, None, None
    # x/y axes of each plot view box, so overlays (e.g. grid lines) can find the axes of the cell they are in
    view_axes: ty.ClassVar[dict[ViewBox, tuple[VispyXAxisVisual, VispyYAxisVisual]]] = {}
    # data node of each plot view box; its transform includes the axis scale, so overlays can map data coordinates
    view_data_scenes: ty.ClassVar[dict[ViewBox, Node]] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # enable hover events
        self._send_hover_events = True  # temporary workaround

        self.events.ignore_callback_errors = False
        self.native.setMinimumSize(QSize(200, 200))
        self.context.set_depth_func("lequal")

        with self.modify_context():
            self.grid = self.central_widget.add_grid(spacing=0)
            self.view = self.grid.add_view(row=1, col=1)

            # this gives small padding to the right of the plot
            self.padding_x = self.grid.add_widget(row=0, col=2)
            self.padding_x.width_max = 20
            # this gives small padding to the top of the plot
            self.padding_y = self.grid.add_widget(row=0, col=0, col_span=2)
            self.padding_y.height_max = 20
            self.view_axes = {}
            self.view_data_scenes = {}

        # connect events
        self.events.add(reset_view=Event, reset_x=Event, reset_y=Event, background_color=Event, context_menu=Event)

    @SceneCanvas_.bgcolor.setter
    def bgcolor(self, color: str | npt.ArrayLike) -> None:
        """Notify visuals when the rendered canvas background changes."""
        previous = self._bgcolor
        SceneCanvas_.bgcolor.fset(self, color)
        if not np.array_equal(previous, self._bgcolor):
            self.events.background_color()

    @contextmanager
    def modify_context(self):
        """Modify context"""
        self.unfreeze()
        yield self
        self.freeze()

    def _process_mouse_event(self, event: MouseEvent) -> None:
        """Ignore mouse wheel events which have modifiers."""
        if event.type == "mouse_wheel" and len(event.modifiers) > 0:
            return
        if event.handled:
            return
        if not hasattr(event, "scale"):
            event.scale = 1.0
        super()._process_mouse_event(event)

    def visual_at(self, pos: ty.Sequence[float]) -> VisualNode | None:
        """Find the interactive visual at a canvas position using the plot layout when possible."""
        widgets = {
            widget for view, (x_axis, y_axis) in self.view_axes.items() for widget in (view, x_axis.node, y_axis.node)
        }
        hit = None
        pending = [self.scene]
        while pending:
            node = pending.pop()
            if not node.visible:
                continue
            if isinstance(node, VisualNode) and node.interactive:
                # Vispy renders the whole scene to pick a pixel. The standard plot targets are rectangular widgets.
                if not isinstance(node, Widget) or node not in widgets or node.margin:
                    return super().visual_at(pos)
                if min(node.size) > 0 and self._widget_contains(node, pos):
                    if hit is not None:
                        return super().visual_at(pos)
                    hit = node
            pending.extend(node.children)
        return hit

    def _on_mouse_double_click(self, event: MouseEvent) -> None:
        """Reset the x- or y-range when the x- or y-axis of any plot cell is double-clicked with the left button.

        Double-clicks in the plot area are left to the viewer and layer callbacks (e.g. finishing a shape).
        """
        if event.button != 1 or event.pos is None:
            return
        axis, view = self._axis_view_at(event.pos)
        if axis == "x":
            self.events.reset_x(view=view)
        elif axis == "y":
            self.events.reset_y(view=view)

    def _axis_at(self, pos: ty.Sequence[float]) -> str | None:
        """Return "x" or "y" when the canvas position `pos` is on the x- or y-axis of any plot cell."""
        return self._axis_view_at(pos)[0]

    def _axis_view_at(self, pos: ty.Sequence[float]) -> tuple[str | None, ViewBox | None]:
        """Identify which cell axis contains the canvas position."""
        for view, (x_axis, y_axis) in self.view_axes.items():
            if self._widget_contains(x_axis.node, pos):
                return "x", view
            if self._widget_contains(y_axis.node, pos):
                return "y", view
        return None, None

    def _widget_contains(self, widget: Widget, pos: ty.Sequence[float]) -> bool:
        """Whether the canvas position `pos` falls inside `widget`."""
        if widget.canvas is not self:
            return False
        x, y = np.asarray(pos[:2], dtype=float) - widget.node_transform(self.central_widget).map([0, 0])[:2]
        width, height = widget.size
        return 0 <= x <= width and 0 <= y <= height


class _PlotCellsGrid(Grid):
    """Keep the data areas aligned when joint panels have different gutters."""

    joint_pairs: tuple[tuple[VispyPlotCell, VispyPlotCell, str], ...] = ()
    joint_size: int | None = None

    def _update_child_widget_dim(self) -> None:
        if self.joint_size is not None:
            self._fix_marginal_thickness(self.joint_size)
        super()._update_child_widget_dim()
        for main, marginal, dimension in self.joint_pairs:
            horizontal = dimension == "width"
            if horizontal:
                main_width = main.y_axis.node.width_max
                if marginal.y_axis.node.width_max != main_width:
                    marginal.y_axis.node.width_max = main_width
                    marginal.layout._need_solver_recreate = True

            limit = f"{dimension}_max"
            sizes = [
                cell.layout.size[0 if horizontal else 1] - _gutter_size(cell, horizontal) for cell in (main, marginal)
            ]

            # A narrow window can give the gutters less space than their maximum size.
            available = min(sizes)
            for cell in (main, marginal):
                cap = available if available > 0 else None
                if getattr(cell.view, limit) != cap:
                    setattr(cell.view, limit, cap)
                    cell.layout._need_solver_recreate = True

    def _fix_marginal_thickness(self, size: int) -> None:
        """Give each marginal layout exactly ``size`` pixels of data area plus its gutters across the shared axis.

        Capping only the view would leave the layout its stretch share of the space, shown as blank space beside the
        marginal; with the layout fixed, the main panel takes all the remaining space.
        """
        for _, marginal, dimension in self.joint_pairs:
            # the top marginal (aligned in width) is `size` tall, the right one (aligned in height) is `size` wide
            horizontal = dimension == "height"
            thickness = size + _gutter_size(marginal, horizontal)
            name = "width" if horizontal else "height"
            layout = marginal.layout
            if getattr(layout, f"{name}_min") != thickness or getattr(layout, f"{name}_max") != thickness:
                setattr(layout, f"{name}_min", thickness)
                setattr(layout, f"{name}_max", thickness)
                self._need_solver_recreate = True


def _gutter_size(cell: VispyPlotCell, horizontal: bool) -> float:
    """Total maximum size of the cell layout's axis and padding tracks (all but the view's) along one dimension."""
    limit = "width_max" if horizontal else "height_max"
    view_track = 1 if horizontal else 0
    gutters: dict[int, float] = {}
    for row, col, rows, cols, widget in cell.layout._grid_widgets.values():
        track, span = (col, cols) if horizontal else (row, rows)
        if track == view_track or span != 1:
            continue
        cap = getattr(widget, limit)
        if cap is not None:
            gutters[track] = min(gutters.get(track, cap), cap)
    return sum(gutters.values())


def _tile_axis(side: str, lengths: list[float], extent: float, padding: float, stacked: bool) -> list[float]:
    """Return the start coordinate of each overlay footprint along one axis of a view.

    Parameters
    ----------
    side : str
        Where the overlays are anchored: ``left``/``top`` (start), ``right``/``bottom`` (end), otherwise centered.
    lengths : list[float]
        Footprint length of each overlay along this axis, in tiling order (first is closest to the anchor).
    extent : float
        Length of the view along this axis.
    padding : float
        Gap between the view edge and the overlays, and between consecutive stacked overlays.
    stacked : bool
        Whether the overlays are placed one after another along this axis or share the same line.
    """
    if not stacked:
        if side in ("left", "top"):
            return [padding for _ in lengths]
        if side in ("right", "bottom"):
            return [extent - length - padding for length in lengths]
        return [(extent - length) / 2 for length in lengths]
    offsets = []
    offset = padding
    for length in lengths:
        offsets.append(offset)
        offset += length + padding
    if side in ("left", "top"):
        return offsets
    if side in ("right", "bottom"):
        return [extent - offset - length for offset, length in zip(offsets, lengths, strict=True)]
    # centered stacking axis: center the whole group instead of overlapping
    shift = (extent - (sum(lengths) + padding * (len(lengths) - 1))) / 2 - padding
    return [offset + shift for offset in offsets]


class VispyCanvas:
    """Line-based vispy canvas"""

    _instances: ty.ClassVar[WeakSet[VispyCanvas]] = WeakSet()
    x_axis, y_axis = None, None

    def __init__(
        self,
        viewer: ViewerModel,
        key_map_handler: KeymapHandler,
        font_manager: QtFontManager,
        font_family: str,
        *args,
        **kwargs,
    ):
        self.max_texture_sizes = None
        self.viewer = viewer
        self._font_info = FontInfo(face=font_family, font_manager=font_manager)
        self._scene_canvas = NapariSceneCanvas(*args, keys=None, vsync=True, **kwargs)
        self._data_scene = Node(parent=self.view.scene)
        self.camera = VispyCamera(self.view, self.viewer.camera, self.viewer)
        # plot cells; the first is the main view and axes, grid mode adds one per layer group
        self._cells: list[VispyPlotCell] = []
        self._joint_top_axis = PlotGridCell(row=0, column=0, y_scale="linear", x_label="", y_label="")
        self._joint_right_axis = PlotGridCell(row=0, column=1, x_scale="linear", x_label="", y_label="")
        self._cells_grid: _PlotCellsGrid | None = None
        self._cells_key: tuple | None = None
        # layers drawn in each plot cell in grid mode; empty outside grid mode
        self._cell_layers: list[list[Layer]] = []
        self._active_cell: VispyPlotCell | None = None
        # canvas position of a right press that may open the context menu on release
        self._context_press: np.ndarray | None = None
        self.viewer.axis.events.x_scale.connect(self._on_axis_scale_change)
        self.viewer.axis.events.y_scale.connect(self._on_axis_scale_change)
        self.viewer.axis.events.x_power.connect(self._on_axis_scale_change)
        self.viewer.axis.events.y_power.connect(self._on_axis_scale_change)
        self.viewer.axis.events.x_inverted.connect(self._on_axis_flip_change)
        self.viewer.axis.events.y_inverted.connect(self._on_axis_flip_change)

        self.layer_to_visual: dict[Layer, VispyBaseLayer] = {}
        # one visual per overlay, or one per plot cell for gridded overlays in grid mode
        self._overlay_to_visual: dict[Overlay, list[VispyBaseOverlay]] = {}
        self._layer_name_visuals: dict[Layer, VispyLayerNameOverlay] = {}
        self._needs_overlay_position_update = True
        self._key_map_handler = key_map_handler
        self._instances.add(self)
        # Call get_max_texture_sizes() here so that we query OpenGL right now while we know a Canvas exists.
        # Later calls to get_max_texture_sizes() will return the same results because it's using an lru_cache.
        self.max_texture_sizes = get_max_texture_sizes()

        # drag tool
        self.tool = VispyDragTool(self.viewer, view=self._data_scene, order=1e6)

        # add x-axis widget
        self.x_axis = VispyXAxisVisual(self.viewer, parent=self.view, order=1e6 + 1)
        self.grid.add_widget(self.x_axis.node, row=2, col=1)
        link_axis(self.x_axis, self.view)

        # add y-axis widget
        self.y_axis = VispyYAxisVisual(self.viewer, parent=self.view, order=1e6 + 1)
        self.grid.add_widget(self.y_axis.node, row=1, col=0)
        link_axis(self.y_axis, self.view)

        self.colorbar = VispyColorBarVisual(self.viewer, self.viewer.colorbar, self._font_info)
        self._cell_colorbars: dict[tuple[int, int], VispyColorBarVisual] = {}
        self._cell_colorbar_paddings: dict[Grid, Widget] = {}

        with self._scene_canvas.modify_context():
            self._scene_canvas.x_axis = self.x_axis
            self._scene_canvas.y_axis = self.y_axis
        self._scene_canvas.view_axes[self.view] = (self.x_axis, self.y_axis)
        self._scene_canvas.view_data_scenes[self.view] = self._data_scene
        self._cells.append(
            VispyPlotCell(self.viewer, self.view, self._data_scene, self.camera, self.x_axis, self.y_axis)
        )
        self._active_cell = self._cells[0]
        self._update_colorbars()
        self.viewer.events.colorbars_change.connect(self._update_colorbars)

        for overlay in self.viewer._overlays.values():
            self._add_overlay_to_visual(overlay)
        self.viewer._overlays.events.added.connect(self._on_overlay_added)
        self.viewer._overlays.events.removed.connect(self._on_overlay_removed)

        # connect events
        # Connecting events from SceneCanvas
        self._scene_canvas.events.key_press.connect(self._key_map_handler.on_key_press)
        self._scene_canvas.events.key_release.connect(self._key_map_handler.on_key_release)

        # self._scene_canvas.events.draw.connect(self.enable_dims_play)
        self._scene_canvas.events.draw.connect(self.camera.on_draw)
        self._scene_canvas.events.reset_view.connect(self.viewer.reset_view)
        self._scene_canvas.events.reset_x.connect(self._reset_cell_axis)
        self._scene_canvas.events.reset_y.connect(self._reset_cell_axis)

        self._scene_canvas.events.mouse_double_click.connect(self._on_mouse_double_click)
        self._scene_canvas.events.mouse_double_click.connect(self._scene_canvas._on_mouse_double_click)
        self._scene_canvas.events.mouse_move.connect(qthrottled(self._on_mouse_move, timeout=5))
        self._scene_canvas.events.mouse_press.connect(self._on_mouse_press)
        self._scene_canvas.events.mouse_release.connect(self._on_mouse_release)
        self._scene_canvas.events.mouse_wheel.connect(self._on_mouse_wheel)

        self._scene_canvas.events.resize.connect(self.on_resize)
        self._scene_canvas.events.draw.connect(self.on_draw)
        self.viewer.cursor.events.style.connect(self._on_cursor)
        self.viewer.cursor.events.size.connect(self._on_cursor)
        self.viewer.events.theme.connect(self._on_theme_change)
        self.viewer.camera.events.mouse_pan.connect(self._on_interactive)
        self.viewer.camera.events.mouse_zoom.connect(self._on_interactive)
        self.viewer.camera.events.zoom.connect(self._on_cursor)
        self.viewer.layers.events.reordered.connect(self._reorder_layers)
        self.viewer.layers.events.reordered.connect(self._update_scenegraph)
        self.viewer.layers.events.removed.connect(self._remove_layer)
        self.viewer.layers.events.connect(self._on_layer_stream)
        self.viewer.canvas.grid.events.connect(self._update_scenegraph)
        self.viewer.canvas.grid.events.cell_changed.connect(self._update_scenegraph)
        self.viewer.events.layers_change.connect(self._refresh_cell_views)
        self.viewer.events.reset_view.connect(self._reset_cell_views)
        self.viewer.events.margins.connect(self._refresh_cell_views)
        self.viewer.events.cell_rect.connect(self._on_cell_rect)

        self.viewer.canvas.events.background_color.connect(self._update_background_color)
        self.viewer.canvas.events._overlay_positions_changed.connect(self._request_overlay_positions)
        self.viewer.canvas.overlay_tiling.events.connect(self._update_overlay_canvas_positions)
        # the plot area changes size without a canvas resize when the axes grow or the colorbar is shown; the grid
        # resizes it while drawing, before the overlays are drawn, so they are placed right away
        self.view.events.resize.connect(self._update_overlay_canvas_positions)
        self.viewer.canvas.events.size.connect(self._on_model_size_change)
        get_settings().appearance.events.font_size.connect(self._update_font_sizes)
        self.destroyed.connect(self._disconnect_theme)
        self._update_background_color()
        self._on_axis_scale_change()

    def _on_axis_scale_change(self, _event: Event | None = None) -> None:
        """Apply the selected axis transforms to scene data."""
        if self.viewer.layers:
            self.viewer._on_update_extent()
            if _event is None or _event.type.endswith("_scale"):
                self.viewer.reset_view()
        self._refresh_cell_views(_event)
        self._scene_canvas.update()

    def _on_axis_flip_change(self, _event: Event | None = None) -> None:
        for cell in self._cells:
            cell.camera._update_flip()

    def _on_layer_stream(self, event: Event) -> None:
        """Refit the bounds of the grid cell that draws a layer whose data was streamed.

        Streaming skips the viewer's extent update to stay fast; in grid mode the cell drawing the layer still has to
        follow its data (e.g. the value axis of an autoscaled joint marginal), which only needs that cell's layers.
        """
        if event.type != "stream" or self._cells_grid is None:
            return
        # the layer list re-emits the event with itself as the current source; the layer is the first one
        streamed = event.sources[0]
        for cell, layers in zip(self._cells, self._cell_layers, strict=False):
            if any(layer is streamed for layer in layers):
                cell.camera.refresh_bounds()
                return

    def _refresh_cell_views(self, event: Event | None = None) -> None:
        """Refresh limits, transforms and axis labels for the layers assigned to each cell.

        When only one layer's data changed (``event.layer``), only the cell that draws it is refreshed.
        """
        grid = self.viewer.canvas.grid
        changed_layer = getattr(event, "layer", None)
        for index, cell in enumerate(self._cells):
            if (
                changed_layer is not None
                and self._cell_layers
                and (index >= len(self._cell_layers) or changed_layer not in self._cell_layers[index])
            ):
                continue
            cell.camera._on_aspect_change()
            if index >= len(self._cell_layers):
                cell.configure_axes(None, None, (True, True))
                continue
            model = grid._find_cell(*cell.position)
            labels_visible = True
            if grid.enabled and grid.joint:
                model = None
                panel = "joint"
                if cell.position == (0, 0) and grid.joint_top:
                    model = self._joint_top_axis
                    model.y_label = grid.joint_top_label
                    model.y_tick_formatter = grid.joint_top_tick_formatter
                    panel = "top"
                elif cell.position[1] == 1:
                    model = self._joint_right_axis
                    model.x_label = grid.joint_right_label
                    model.x_tick_formatter = grid.joint_right_tick_formatter
                    panel = "right"
                labels_visible = panel not in grid.joint_hidden_labels
            field = getattr(event, "field", getattr(event, "type", ""))
            changed_model = getattr(event, "cell", None)
            reset = tuple(
                field in (f"{name}lim", f"{name}_scale", f"{name}_categories")
                and (changed_model is None or changed_model is model)
                for name in ("x", "y")
            )
            shared = (grid.sharex, grid.sharey)
            if grid.joint:
                shared = (cell.position[1] == 0, cell.position[0] == int(grid.joint_top))
            cell.configure_axes(
                model,
                self._cell_layers[index],
                shared,
                reset=reset,
                labels_visible=labels_visible,
                own_formatters=(not shared[0], not shared[1]) if grid.enabled and grid.joint else (False, False),
            )
        self._update_crosshair_lines()

    def _update_crosshair_lines(self) -> None:
        """Draw only the shared-axis line of the crosshair in joint marginals (both lines everywhere else)."""
        grid = self.viewer.canvas.grid
        joint = grid.enabled and grid.joint and self._cells_grid is not None
        for overlay, visuals in self._overlay_to_visual.items():
            if not isinstance(overlay, CrosshairOverlay):
                continue
            for index, visual in enumerate(visuals):
                lines = self._cells[index].camera._shared if joint and index < len(self._cells) else (True, True)
                if visual.node.lines != lines:
                    visual.node.lines = lines
                    visual.node.update()

    def _reset_cell_axis(self, event: Event) -> None:
        name = "x" if event.type == "reset_x" else "y"
        cell = next((cell for cell in self._cells if cell.view is getattr(event, "view", None)), self._cells[0])
        if not cell.camera.reset_cell_axis(name):
            reset = self.viewer.reset_x_view if name == "x" else self.viewer.reset_y_view
            reset()

    def _on_cell_rect(self, event: Event) -> None:
        """Show the own limits set for a grid cell (e.g. by ``viewer.set_cell_rect``)."""
        if self._cells_grid is None:
            return
        for cell in self._cells:
            if cell.position == event.cell:
                # cells publish their own limits while they are panned; only apply limits set elsewhere
                if cell.camera._local_rect is not None and tuple(cell.camera._local_rect) != event.rect:
                    cell.camera.restore_cell_rect(event.rect)
                return

    def _reset_cell_views(self, _event: Event | None = None) -> None:
        for cell in self._cells:
            for name in ("x", "y"):
                cell.camera.reset_cell_axis(name)

    def _grid_active(self) -> bool:
        """Whether layers are shown in a grid of plot cells."""
        return bool(self.viewer.canvas.grid.enabled and (self.viewer.layers or self.viewer.canvas.grid.joint))

    def _update_scenegraph(self, _event: Event | None = None) -> None:
        """Lay out the plot cells and put each layer in the cell of its group (a single cell outside grid mode)."""
        if getattr(_event, "type", None) == "spacing":
            self._update_grid_spacing()
            return
        viewboxes = []
        if self._grid_active():
            grid = self.viewer.canvas.grid
            contents = dict(grid.iter_viewboxes(self.viewer.layers))
            if grid.joint:
                positions = [(int(grid.joint_top), 0)]
                if grid.joint_top:
                    positions.append((0, 0))
                if grid.joint_right:
                    positions.append((int(grid.joint_top), 1))
                viewboxes = [(position, contents[position]) for position in positions]
            else:
                assigned = (
                    {(cell.row, cell.column) for cell in grid.cells if cell.group is not None}
                    if grid.group_by_metadata
                    else set()
                )
                viewboxes = [
                    (position, indices) for position, indices in contents.items() if indices or position in assigned
                ]
        if viewboxes:
            self._layout_cells([position for position, _ in viewboxes])
            self._cell_layers = [[self.viewer.layers[index] for index in indices] for _, indices in viewboxes]
            for cell, (position, indices) in zip(self._cells, viewboxes, strict=True):
                cell.position = position
                for index in indices:
                    layer = self.viewer.layers[index]
                    if layer in self.layer_to_visual:
                        self.layer_to_visual[layer].node.parent = cell.data_scene
                        self._layer_name_visuals[layer].node.parent = cell.view
        else:
            self._layout_single()
            self._cell_layers = []
            self._cells[0].position = (0, 0)
            for layer, vispy_layer in self.layer_to_visual.items():
                vispy_layer.node.parent = self._data_scene
                self._layer_name_visuals[layer].node.parent = self.view
        self._update_first_visible()
        self._refresh_cell_views(_event)
        self._update_gridded_overlays()
        self._update_colorbars()
        self._on_interactive()
        self._request_overlay_positions()

    def _layout_cells(self, positions: list[tuple[int, int]]) -> None:
        """Show one plot cell per grid position, reusing existing cells; the first cell is the main view."""
        while len(self._cells) < len(positions):
            self._cells.append(self._create_cell())
        while len(self._cells) > len(positions):
            self._close_cell(self._cells.pop())

        if self._cells_grid is None:
            for widget in self._cells[0].widgets:
                detach_widget(self.grid, widget)
            spacing = self.viewer.canvas.grid._compute_canvas_spacing(self._scene_canvas.size, self.viewer.layers)
            self._cells_grid = _PlotCellsGrid(spacing=spacing)
            self.grid.add_widget(self._cells_grid, row=1, col=0, col_span=2)
        else:
            self._update_grid_spacing()
        key = (
            tuple(positions),
            self.viewer.canvas.grid.joint,
            self.viewer.canvas.grid.joint_ratio,
            self.viewer.canvas.grid.joint_size,
        )
        if key == self._cells_key:
            return
        container = self._cells_grid
        grid = self.viewer.canvas.grid
        pairs = []
        for cell, (row, col) in zip(self._cells, positions, strict=True):
            layout = cell.ensure_layout()
            cell.view.width_max = None
            cell.view.height_max = None
            cell.view.width_min = 0
            cell.view.height_min = 0
            # `_PlotCellsGrid` fixes the marginal layouts again when `joint_size` is set
            layout.width_min = layout.height_min = 0
            layout.width_max = layout.height_max = None
            layout._need_solver_recreate = True
            joint = grid.joint
            top = joint and row == 0 and grid.joint_top
            right = joint and col == 1
            cell.x_axis.suppress(bool(top))
            cell.y_axis.suppress(bool(right))
            if top:
                pairs.append((self._cells[0], cell, "width"))
            if right:
                pairs.append((self._cells[0], cell, "height"))
            if joint:
                ratio = grid.joint_ratio
                layout.stretch = (
                    ratio if col == 0 else 1,
                    ratio if row == int(grid.joint_top) else 1,
                )
                if grid.joint_size is not None:
                    # the marginals keep a fixed thickness and the main panel takes the rest
                    if top:
                        cell.view.height_min = cell.view.height_max = grid.joint_size
                    if right:
                        cell.view.width_min = cell.view.width_max = grid.joint_size
            else:
                layout.stretch = (1, 1)
            if layout.parent is not container:
                container.add_widget(layout, row=row, col=col)
                layout._need_solver_recreate = True
        # Reposition attached layouts without replacing their solver variables.
        container._grid_widgets = {
            index: (row, col, 1, 1, cell.layout)
            for index, (cell, (row, col)) in enumerate(zip(self._cells, positions, strict=True))
        }
        container._cells = {}
        for cell, (row, col) in zip(self._cells, positions, strict=True):
            container._cells.setdefault(row, {})[col] = cell.layout
        container._n_added = len(positions)
        container._next_cell = [positions[-1][0], positions[-1][1] + 1]
        container.joint_pairs = tuple(pairs)
        container.joint_size = grid.joint_size if grid.joint else None
        container._need_solver_recreate = True
        self._cells_key = key

    def _update_grid_spacing(self) -> None:
        """Update the existing grid when the computed pixel spacing changes."""
        if self._cells_grid is None:
            return
        spacing = self.viewer.canvas.grid._compute_canvas_spacing(self._scene_canvas.size, self.viewer.layers)
        if spacing != self._cells_grid.spacing:
            self._cells_grid.spacing = spacing
            self._scene_canvas.update()

    def _layout_single(self) -> None:
        """Close the extra plot cells and put the main view and axes back in the canvas grid."""
        if self._cells_grid is None:
            return
        while len(self._cells) > 1:
            self._close_cell(self._cells.pop())
        main = self._cells[0]
        main.view.width_max = None
        main.view.height_max = None
        for widget in main.widgets:
            detach_widget(main.layout, widget)
        main.layout = None
        detach_widget(self.grid, self._cells_grid)
        self._cells_grid = None
        self._cells_key = None
        self.grid.add_widget(self.view, row=1, col=1)
        self.grid.add_widget(self.x_axis.node, row=2, col=1)
        self.grid.add_widget(self.y_axis.node, row=1, col=0)
        # the grid ties row heights and column widths to the first widget it lists in each column/row (weak
        # constraints), so the view must come first again, as when the canvas was made, or the axes shrink to the
        # size of the paddings
        widgets = self.grid._grid_widgets
        main_keys = [key for key, value in widgets.items() if value[-1] in main.widgets]
        self.grid._grid_widgets = {
            key: widgets[key] for key in [*main_keys, *(k for k in widgets if k not in main_keys)]
        }
        self._set_active_cell(main)

    def _create_cell(self) -> VispyPlotCell:
        """Create a plot cell that follows the camera, axis scales and overlay tiling of the main view."""
        cell = VispyPlotCell.create(self.viewer)
        self._scene_canvas.events.draw.connect(cell.camera.on_draw)
        cell.view.events.resize.connect(self._update_overlay_canvas_positions)
        self._scene_canvas.view_axes[cell.view] = (cell.x_axis, cell.y_axis)
        self._scene_canvas.view_data_scenes[cell.view] = cell.data_scene
        return cell

    def _close_cell(self, cell: VispyPlotCell) -> None:
        """Disconnect and remove a plot cell created for grid mode."""
        self._scene_canvas.events.draw.disconnect(cell.camera.on_draw)
        cell.view.events.resize.disconnect(self._update_overlay_canvas_positions)
        self._scene_canvas.view_axes.pop(cell.view, None)
        self._scene_canvas.view_data_scenes.pop(cell.view, None)
        if self._active_cell is cell:
            self._set_active_cell(self._cells[0])
        cell.close()

    def _set_active_cell(self, cell: VispyPlotCell) -> None:
        """Use `cell` for mouse interaction, drawing the drag tool (box zoom, lasso) in it."""
        if cell is self._active_cell:
            return
        self._active_cell = cell
        self.tool._polygon.node.parent = cell.data_scene

    def _update_colorbars(self, _event: Event | None = None) -> None:
        """Attach the figure colorbar and any configured per-cell colorbars."""
        tiled = self._cells_grid is not None
        self.colorbar.place(
            self.grid, 1, 2 if tiled else 3, 0 if tiled else 1, self._scene_canvas.padding_x, 2 if tiled else 1
        )
        layouts = {cell.position: cell.layout for cell in self._cells if cell.layout is not None}
        stale_positions = self._cell_colorbars.keys() - layouts.keys()
        for position in stale_positions:
            self._cell_colorbars.pop(position).close()
        for layout in self._cell_colorbar_paddings.keys() - set(layouts.values()):
            detach_widget(layout, self._cell_colorbar_paddings.pop(layout))
        for position, layout in layouts.items():
            if layout not in self._cell_colorbar_paddings:
                padding = layout.add_widget(row=1, col=2)
                padding.width_max = 0
                self._cell_colorbar_paddings[layout] = padding
            model = self.viewer._cell_colorbars.get(position)
            if model is None:
                continue
            if position not in self._cell_colorbars:
                self._cell_colorbars[position] = VispyColorBarVisual(self.viewer, model, self._font_info)
            self._cell_colorbars[position].place(layout, 0, 2, 1, self._cell_colorbar_paddings[layout])

    def _update_gridded_overlays(self) -> None:
        """Give gridded overlays one visual per plot cell; other overlays stay in the first cell."""
        for overlay, visuals in self._overlay_to_visual.items():
            gridded = overlay.gridded if isinstance(overlay, CanvasOverlay) else True
            wanted = len(self._cells) if gridded and self._cells_grid is not None else 1
            if not overlay.visible and len(visuals) < wanted:
                wanted = len(visuals)
            while len(visuals) > wanted:
                visuals.pop().close()
            for index in range(len(visuals), wanted):
                layer_filter = self._legend_filter(index) if isinstance(overlay, LegendOverlay) else None
                visuals.append(self._create_overlay_visual(overlay, self._cells[index], layer_filter))
        self._update_legend_filters()
        self._update_crosshair_lines()

    def _update_legend_filters(self, _event: Event | None = None) -> None:
        """List in each cell's copy of a gridded legend only the layers drawn in that cell.

        The first cell also lists rows of layers that are in no cell, so they stay visible and clickable.
        """
        for overlay, visuals in self._overlay_to_visual.items():
            if not isinstance(overlay, LegendOverlay):
                continue
            for index, visual in enumerate(visuals):
                visual.set_layer_filter(
                    self._legend_filter(index) if self._cells_grid is not None and overlay.gridded else None
                )

    def _legend_filter(self, index: int) -> tuple[frozenset[str], bool] | None:
        if not self._cell_layers:
            return None
        if index == 0:
            return (frozenset(layer.name for layers in self._cell_layers[1:] for layer in layers), False)
        return (frozenset(layer.name for layer in self._cell_layers[index]), True)

    @property
    def events(self):
        # This is backwards compatible with the old events system
        # https://github.com/napari/napari/issues/7054#issuecomment-2205548968
        return self._scene_canvas.events

    @property
    def destroyed(self) -> pyqtBoundSignal:
        """Get destroyed signal"""
        return self._scene_canvas._backend.destroyed

    @property
    def native(self) -> CanvasBackendDesktop:
        """Returns the native widget of the Vispy SceneCanvas."""
        return self._scene_canvas.native

    @property
    def screen_changed(self) -> ty.Callable:
        """Bound method returning signal indicating whether the window screen has changed."""
        return self._scene_canvas._backend.screen_changed

    @property
    def view(self):
        """Canvas view."""
        return self._scene_canvas.view

    @property
    def grid(self):
        """Canvas grid."""
        return self._scene_canvas.grid

    def font_info(self) -> FontInfo:
        """Get the shared font information used by overlay/layer text visuals."""
        return self._font_info

    @property
    def background_color_override(self) -> np.ndarray | None:
        """Return the canvas model's optional background override."""
        return self.viewer.canvas.background_color_override

    @background_color_override.setter
    def background_color_override(self, value: str | np.ndarray | None) -> None:
        self.viewer.canvas.background_color_override = value

    def _on_theme_change(self, event: Event) -> None:
        self._update_background_color()

    def _update_background_color(self, _event: Event | None = None) -> None:
        self.bgcolor = self.viewer.canvas.background_color

    def _on_model_size_change(self, _event: Event | None = None) -> None:
        if self.size != self.viewer.canvas.size:
            self.size = self.viewer.canvas.size

    def _request_overlay_positions(self, _event: Event | None = None) -> None:
        self._needs_overlay_position_update = True
        self._scene_canvas.update()

    def _view_size(self, view: int) -> tuple[float, float]:
        """Return the (width, height) in pixels of the view box of plot cell `view` (excluding axes and colorbar)."""
        width, height = self._cells[view].view.size
        return float(width), float(height)

    def _get_ordered_visible_canvas_overlays(
        self,
        target: int | None = None,
    ) -> Iterator[tuple[CanvasOverlay, VispyCanvasOverlay, int]]:
        """Iterate over visible, tileable canvas overlays in tiling order.

        Yields the overlay model, its visual and the index of the plot cell it is drawn in (0 is the main view; gridded
        overlays have one visual per cell in grid mode). Canvas overlays are ordered by ``viewer.canvas.overlays``,
        followed by layer names in their respective plot cells. Overlays without a ``CanvasPosition`` (e.g. the brush
        circle) and visuals without a size (e.g. grid lines, empty text) are skipped.
        """
        for overlay in self.viewer._overlays.values():
            if not (
                isinstance(overlay, CanvasOverlay) and overlay.visible and overlay.position in list(CanvasPosition)
            ):
                continue
            visuals = self._overlay_to_visual.get(overlay, [])
            indices = range(len(visuals)) if target is None else (target,)
            for view in indices:
                if view >= min(len(visuals), len(self._cells)):
                    continue
                visual = visuals[view]
                if (
                    visual.x_size > 0
                    and visual.y_size > 0
                    and not (isinstance(overlay, LegendOverlay) and overlay.outside)
                ):
                    yield overlay, visual, view
        view_indices = {cell.view: index for index, cell in enumerate(self._cells)}
        layers = (
            self._cell_layers[target] if target is not None and target < len(self._cell_layers) else self.viewer.layers
        )
        for layer in layers:
            visual = self._layer_name_visuals.get(layer)
            if visual is not None and visual.node.visible and visual.x_size > 0 and visual.y_size > 0:
                view = view_indices.get(visual.node.parent)
                if view is not None:
                    yield visual.overlay, visual, view

    def _update_overlay_canvas_positions(self, _event: Event | None = None) -> None:
        """Tile visible canvas overlays so overlays sharing a position stack instead of overlapping.

        Follows napari's tiling: per view and position, overlays are placed one after another along the direction set
        in ``viewer.canvas.overlay_tiling``, separated by its padding. Unlike napari, a group whose stacking axis is
        centered (e.g. ``middle_center``) is centered as a whole instead of overlapping.
        """
        # A view resize only affects overlays in that view.
        source = getattr(_event, "source", None)
        target = next((i for i, cell in enumerate(self._cells) if cell.view is source), None)
        # refresh sizes first; the size-changed event is blocked since the overlays are placed right after
        with self.viewer.canvas.events._overlay_positions_changed.blocker():
            for overlay, visuals in self._overlay_to_visual.items():
                if isinstance(overlay, CanvasOverlay):
                    selected = visuals if target is None else visuals[target : target + 1]
                    for index, visual in enumerate(selected, start=target or 0):
                        visual._on_position_change()
                        if isinstance(overlay, LegendOverlay):
                            cell = self._cells[index]
                            visual.place(cell.view, cell.layout or self.grid, 0 if cell.layout is not None else 1)
            layers = (
                self._cell_layers[target]
                if target is not None and target < len(self._cell_layers)
                else self.viewer.layers
            )
            for layer in layers:
                visual = self._layer_name_visuals.get(layer)
                if visual is not None and visual.node.visible:
                    visual._on_position_change()

        tiling = self.viewer.canvas.overlay_tiling
        x_padding, y_padding = tiling.padding
        groups: dict[tuple[int, CanvasPosition], list[VispyCanvasOverlay]] = {}
        for overlay, visual, view in self._get_ordered_visible_canvas_overlays(target):
            groups.setdefault((view, CanvasPosition(overlay.position)), []).append(visual)

        for (view, position), visuals in groups.items():
            width, height = self._view_size(view)
            vertical_side, horizontal_side = str(position).split("_")
            horizontal = getattr(tiling, str(position)) == Orientation.HORIZONTAL
            margins = [getattr(visual, "tile_margin", (0.0, 0.0)) for visual in visuals]
            widths = [visual.x_size + 2 * mx for visual, (mx, _) in zip(visuals, margins, strict=True)]
            heights = [visual.y_size + 2 * my for visual, (_, my) in zip(visuals, margins, strict=True)]
            xs = _tile_axis(horizontal_side, widths, width, x_padding, stacked=horizontal)
            ys = _tile_axis(vertical_side, heights, height, y_padding, stacked=not horizontal)
            for visual, (mx, my), x, y in zip(visuals, margins, xs, ys, strict=True):
                visual.node.transform.translate = [max(0.0, x + mx), max(0.0, y + my), 0, 0]
        if target is None:
            self._needs_overlay_position_update = False

    def _update_font_sizes(self, _event: Event | None = None) -> None:
        font_size = get_settings().appearance.font_size
        overlay_visuals = [visual for visuals in self._overlay_to_visual.values() for visual in visuals]
        for visual in (*overlay_visuals, *self.layer_to_visual.values(), *self._layer_name_visuals.values()):
            visual.set_default_font_size(font_size)

    def _disconnect_theme(self) -> None:
        disconnect_events(self.viewer.events, self)
        disconnect_events(self.viewer.axis.events, self)
        disconnect_events(self.viewer.canvas.events, self)
        disconnect_events(self.viewer.canvas.overlay_tiling.events, self)
        disconnect_events(self.viewer.canvas.grid.events, self)
        disconnect_events(get_settings().appearance.events, self)
        disconnect_events(self.viewer._overlays.events, self)
        self.viewer.layers.events.disconnect(self._on_layer_stream)
        for layer in self.layer_to_visual:
            layer.events.metadata.disconnect(self._on_layer_metadata_change)
        for overlay in self._overlay_to_visual:
            overlay.events.position.disconnect(self._update_overlay_canvas_positions)
            overlay.events.visible.disconnect(self._on_overlay_visibility_change)
            if isinstance(overlay, LegendOverlay):
                overlay.events.outside.disconnect(self._update_overlay_canvas_positions)
            if isinstance(overlay, CanvasOverlay):
                overlay.events.gridded.disconnect(self._update_scenegraph)

    @property
    def bgcolor(self) -> str:
        """Background color of the vispy scene canvas as a hex string. The setter expects str
        (any in vispy.color.get_color_names) or hex starting with # or a tuple | np.array ({3,4},)
        with values between 0 and 1."""
        return self._scene_canvas.bgcolor.hex

    @bgcolor.setter
    def bgcolor(self, value: str | npt.ArrayLike) -> None:
        self._scene_canvas.bgcolor = value

    @property
    def central_widget(self) -> Widget:
        """Overrides SceneCanvas.central_widget to make border_width=0"""
        if self._scene_canvas._central_widget is None:
            self._scene_canvas._central_widget = Widget(
                size=self.size,
                parent=self._scene_canvas.scene,
                border_width=0,
            )
        return self._scene_canvas._central_widget

    @property
    def size(self) -> tuple[int, int]:
        """Return canvas size as tuple (height, width) or accepts size as tuple (height, width)
        and sets Vispy SceneCanvas size as (width, height)."""
        return self._scene_canvas.size[::-1]

    @size.setter
    def size(self, size: tuple[int, int]):
        self._scene_canvas.size = size[::-1]

    @property
    def cursor(self) -> QCursor:
        """Cursor associated with native widget"""
        return self.native.cursor()

    @cursor.setter
    def cursor(self, q_cursor: QCursor | Qt.CursorShape):
        """Setting the cursor of the native widget"""
        self.native.setCursor(q_cursor)

    def _on_cursor(self) -> None:
        """Create a QCursor based on the napari cursor settings and set in Vispy."""

        cursor = self.viewer.cursor.style
        brush_overlay = self.viewer._brush_circle_overlay
        brush_overlay.visible = False

        if cursor in {"square", "circle", "circle_frozen"}:
            # Scale size by zoom if needed
            size = self.viewer.cursor.size
            if self.viewer.cursor.scaled:
                size *= self.viewer.camera.zoom

            size = int(size)

            # make sure the square fits within the current canvas
            if (size < 8 or size > (min(*self.size) - 4)) and cursor != "circle_frozen":
                self.cursor = QtCursorVisual["cross"].value
            elif cursor.startswith("circle"):
                brush_overlay.size = size
                if cursor == "circle_frozen":
                    self.cursor = QtCursorVisual["standard"].value
                    brush_overlay.position_is_frozen = True
                else:
                    self.cursor = QtCursorVisual.blank()
                    brush_overlay.position_is_frozen = False
                brush_overlay.visible = True
            else:
                self.cursor = QtCursorVisual.square(size)
        elif cursor == "crosshair":
            self.cursor = QtCursorVisual.crosshair()
        else:
            self.cursor = QtCursorVisual[cursor].value

    def delete(self) -> None:
        """Schedules the native widget for deletion"""
        self._disconnect_theme()
        self.colorbar.close()
        for colorbar in self._cell_colorbars.values():
            colorbar.close()
        for layer in self.layer_to_visual:
            layer.events.name.disconnect(self._update_legend_filters)
        while len(self._cells) > 1:
            self._close_cell(self._cells.pop())
        for visuals in self._overlay_to_visual.values():
            for visual in visuals:
                visual.node.parent = None
                visual.close()
        self._overlay_to_visual.clear()
        for visual in self._layer_name_visuals.values():
            visual.close()
        self._layer_name_visuals.clear()
        self.native.deleteLater()

    def _on_interactive(self) -> None:
        """Link interactive attributes of view and viewer."""
        interactive = self.viewer.camera.mouse_zoom or self.viewer.camera.mouse_pan
        for cell in self._cells:
            cell.view.interactive = interactive

    def _view_offset(self, view) -> np.ndarray:
        """Return the top-left corner of `view` in canvas pixels."""
        return np.asarray(view.node_transform(self._scene_canvas.central_widget).map([0, 0])[:2])

    def _cell_at(self, position) -> VispyPlotCell:
        """Return the plot cell under the canvas `position`, or the last one the mouse was in."""
        if len(self._cells) > 1:
            for cell in self._cells:
                x, y = np.asarray(position[:2], dtype=float) - self._view_offset(cell.view)
                width, height = cell.view.size
                if 0 <= x <= width and 0 <= y <= height:
                    return cell
        return self._active_cell or self._cells[0]

    def _map_canvas2world(self, position, view: ViewBox | None = None):
        """Map position from canvas pixels into world coordinates.

        Parameters
        ----------
        position : 2-tuple
            Position in canvas (x, y).
        view : ViewBox, optional
            View whose camera maps the position; defaults to the plot cell under `position`.

        Returns
        -------
        coords : tuple
            Position in world coordinates, matches the total dimensionality
            of the viewer.
        """
        cell = self._cell_at(position) if view is None else next(cell for cell in self._cells if cell.view is view)
        view = cell.view
        position = list(np.asarray(position[:2], dtype=float) - self._view_offset(view))
        transform = view.camera.transform.inverse
        mapped_position = transform.map(position)[:2]
        x, y = cell.camera.to_data(*mapped_position)
        return y, x

    def _process_mouse_event(self, mouse_callbacks, event):
        """Called whenever mouse pressed in canvas.
        Parameters
        ----------
        mouse_callbacks : function
            Mouse callbacks function.
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        if event.pos is None:
            return None

        cell = self._cell_at(event.pos)
        if getattr(event, "press_event", None) is not None and event.type in ("mouse_move", "mouse_release"):
            cell = self._active_cell or cell
        event.scale = 1.0
        napari_event = NapariMouseEvent(
            event=event,
            view_direction=None,
            up_direction=None,
            camera_zoom=cell.camera.zoom,
            position=self._map_canvas2world(event.pos, cell.view),
            dims_displayed=[0, 1],
            dims_point=list(self.viewer.dims.point),
            viewbox=cell.position,
        )
        napari_event.plot_rect = cell.camera.rect
        napari_event.plot_selection_tool = self.viewer.drag_tool.active in SELECT_TOOLS
        napari_event.joint_panel = self._joint_panel(cell)
        napari_event.joint_locked = cell.camera.camera.locked_axis is not None
        self.viewer._cursor_panel = napari_event.joint_panel

        # Add the view ray to the event
        event.view_direction = None  # always None because we will display 2d data
        event.up_direction = None  # always None because we will display 2d data

        # Update the cursor position
        self.viewer.cursor._view_direction = napari_event.view_direction
        self.viewer.cursor.position = napari_event.position

        # Put a read only wrapper on the event
        read_only_event = ReadOnlyWrapper(napari_event, exceptions=("handled", "scale"))
        mouse_callbacks(self.viewer, read_only_event)

        layer = self.viewer.layers.selection.active
        if layer is not None:
            mouse_callbacks(layer, read_only_event)

        event.handled = napari_event.handled
        return napari_event

    def _joint_panel(self, cell: VispyPlotCell) -> str | None:
        """Joint-grid panel (``"joint"``, ``"top"`` or ``"right"``) shown by `cell`, or None outside joint mode."""
        grid = self.viewer.canvas.grid
        if not (grid.enabled and grid.joint and self._cells_grid is not None):
            return None
        row, column = cell.position
        if column == 1:
            return "right"
        if grid.joint_top and row == 0:
            return "top"
        return "joint"

    def _on_mouse_double_click(self, event):
        """Called whenever a mouse double-click happen on the canvas

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method. The `event.type` will always be `mouse_double_click`

        Notes
        -----

        Note that this triggers in addition to the usual mouse press and mouse release.
        Therefore a double click from the user will likely triggers the following event in sequence:

             - mouse_press
             - mouse_release
             - mouse_double_click
             - mouse_release
        """
        napari_event = self._process_mouse_event(mouse_double_click_callbacks, event)
        # a double-click in the plot area of an autoscaled joint marginal shows the whole range of its shared axis
        if (
            napari_event is not None
            and not napari_event.handled
            and event.button == 1
            and napari_event.joint_locked
            and self._scene_canvas._axis_at(event.pos) is None
        ):
            if napari_event.joint_panel == "top":
                self.viewer.reset_x_view()
            else:
                self.viewer.reset_y_view()
            event.handled = True

    def _on_mouse_move(self, event):
        """Called whenever mouse moves over canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        if self._context_press is not None and self._moved_from(self._context_press, event):
            self._context_press = None
        self._process_mouse_event(mouse_move_callbacks, event)

    def _on_mouse_press(self, event):
        """Called whenever mouse pressed in canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        self._context_press = self._context_press_position(event)
        # a right-drag on an axis pans along it (see `plot_cell._on_axis_mouse`); the drag tools must not start
        if (
            event.button == 2
            and not event.modifiers
            and self.viewer.camera.mouse_pan
            and event.pos is not None
            and self._scene_canvas._axis_at(event.pos) is not None
        ):
            return
        if event.pos is not None:
            cell = self._cell_at(event.pos)
            self._set_active_cell(cell)
            self.viewer.drag_tool.panel = self._joint_panel(cell)
        self._process_mouse_event(mouse_press_callbacks, event)

    def _on_mouse_release(self, event):
        """Called whenever mouse released in canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        self._process_mouse_event(mouse_release_callbacks, event)
        press, self._context_press = self._context_press, None
        if press is not None and event.button == 2 and not self._moved_from(press, event):
            self._scene_canvas.events.context_menu(pos=tuple(press))

    @staticmethod
    def _moved_from(press: np.ndarray, event) -> bool:
        """Whether the mouse moved far enough from the press to count as a drag (e.g. a right-drag pan)."""
        return (
            event.pos is None or np.hypot(*(np.asarray(event.pos[:2], dtype=float) - press)) >= _CONTEXT_MENU_MAX_MOVE
        )

    def _context_press_position(self, event) -> np.ndarray | None:
        """Return the position of a right press that can open the context menu, or None.

        A right click cancels an unfinished selection (polygon, lasso or box), so it does not open the menu then.
        """
        if event.button != 2 or event.modifiers or event.pos is None:
            return None
        drag_tool = self.viewer.drag_tool
        if drag_tool.active in SELECT_TOOLS and drag_tool.tool is not None and drag_tool.tool.visible:
            return None
        return np.asarray(event.pos[:2], dtype=float)

    def _on_mouse_wheel(self, event):
        """Called whenever mouse wheel activated in canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        self._process_mouse_event(mouse_wheel_callbacks, event)

    @property
    def _canvas_corners_in_world(self):
        """Location of the corners of canvas in world coordinates.

        Returns
        -------
        corners : 2-tuple
            Coordinates of top left and bottom right canvas pixel in the world.
        """
        return self._cell_corners_in_world(self._cells[0])

    def _cell_corners_in_world(self, cell: VispyPlotCell) -> np.ndarray:
        if self._cells_grid is None:
            offset = np.zeros(2)
            size = self._scene_canvas.size
        else:
            offset = self._view_offset(cell.view)
            size = cell.view.size
        return np.array([self._map_canvas2world(offset, cell.view), self._map_canvas2world(offset + size, cell.view)])

    @property
    def _draw_shape_threshold(self) -> tuple[float, float]:
        """Canvas pixels spanned by `_canvas_corners_in_world`: the canvas, or one cell in grid mode."""
        return tuple(self._scene_canvas.size if self._cells_grid is None else self.view.size)

    def on_draw(self, _event: DrawEvent) -> None:
        """Called whenever the canvas is drawn.

        This is triggered from vispy whenever new data is sent to the canvas or
        the camera is moved and is connected in the `QtViewer`.
        """
        # The canvas corners in full world coordinates (i.e. across all layers).
        if self._needs_overlay_position_update:
            self._update_overlay_canvas_positions()
        cell_layers = self._cell_layers or [self.viewer.layers]
        for cell, layers in zip(self._cells, cell_layers, strict=True):
            world_corners = self._cell_corners_in_world(cell)
            threshold = self._draw_shape_threshold if self._cells_grid is None else cell.view.size
            for layer in layers:
                if layer.ndim <= 2:
                    layer._update_draw(
                        scale_factor=1 / cell.camera.zoom,
                        corner_pixels_displayed=world_corners[:, -layer.ndim :],
                        shape_threshold=threshold,
                    )

    def on_resize(self, event: ResizeEvent) -> None:
        """Called whenever canvas is resized."""
        self.viewer._canvas_size = self.size
        self._update_grid_spacing()
        self._update_overlay_canvas_positions()

    def add_layer_visual_mapping(self, napari_layer: Layer, vispy_layer: VispyBaseLayer) -> None:
        """Maps a napari layer to its corresponding vispy layer and sets the parent scene of the vispy layer.

        Parameters
        ----------
        napari_layer :
            Any napari layer, the layer type is the same as the vispy layer.
        vispy_layer :
            Any vispy layer, the layer type is the same as the napari layer.

        Returns
        -------
        None
        """

        vispy_layer.node.parent = self._data_scene
        self.layer_to_visual[napari_layer] = vispy_layer
        label = create_vispy_overlay(
            overlay=napari_layer.name_overlay,
            viewer=self.viewer,
            layer=napari_layer,
            font_info=self._font_info,
            parent=self.view,
        )
        self._layer_name_visuals[napari_layer] = label
        font_size = get_settings().appearance.font_size
        vispy_layer.set_default_font_size(font_size)
        label.set_default_font_size(font_size)
        napari_layer.events.visible.connect(self._reorder_layers)
        napari_layer.events.visible.connect(self._update_scenegraph)
        napari_layer.events.name.connect(self._update_legend_filters)
        napari_layer.events.metadata.connect(self._on_layer_metadata_change)
        # self.viewer.camera.events.angles.connect(vispy_layer._on_camera_move)
        self._reorder_layers()
        self._update_scenegraph()

    def _on_layer_metadata_change(self, _event: Event | None = None) -> None:
        if self.viewer.canvas.grid.enabled and (
            self.viewer.canvas.grid.group_by_metadata or self.viewer.canvas.grid.joint
        ):
            self._update_scenegraph()

    def _remove_layer(self, event):
        """When a layer is removed, remove its parent."""
        layer = event.value
        layer.events.visible.disconnect(self._reorder_layers)
        layer.events.visible.disconnect(self._update_scenegraph)
        layer.events.name.disconnect(self._update_legend_filters)
        layer.events.metadata.disconnect(self._on_layer_metadata_change)
        self._layer_name_visuals.pop(layer).close()
        vispy_layer = self.layer_to_visual[layer]
        vispy_layer.close()
        del vispy_layer
        del self.layer_to_visual[layer]
        self._reorder_layers()
        self._update_scenegraph()

    def _reorder_layers(self):
        """When the list is reordered, propagate changes to draw order."""
        for i, layer in enumerate(self.viewer.layers):
            vispy_layer = self.layer_to_visual.get(layer)
            if vispy_layer is None:
                continue  # added to the layer list, its visual is made next (a callback can run in between)
            vispy_layer.order = i
        self._update_first_visible()

        self._scene_canvas._draw_order.clear()
        self._scene_canvas.update()

    def _update_first_visible(self) -> None:
        """Mark the bottommost visible layer of each plot cell.

        napari blends that layer with the background differently (e.g. additive blending does not add to the
        background colour). Every plot cell draws on its own background, so in grid mode each cell has one; a layer in
        another cell must not take that role from the bottom layer of a cell.
        """
        cell_of = {id(layer): index for index, layers in enumerate(self._cell_layers) for layer in layers}
        found = set()
        for layer in self.viewer.layers:
            vispy_layer = self.layer_to_visual.get(layer)
            if vispy_layer is None:
                continue
            cell = cell_of.get(id(layer))
            first = bool(layer.visible) and cell not in found
            if first:
                found.add(cell)
            if vispy_layer.first_visible != first:
                vispy_layer.first_visible = first
                vispy_layer._on_blending_change()

    def _create_overlay_visual(
        self, overlay: Overlay, cell: VispyPlotCell, layer_filter: tuple[frozenset[str], bool] | None = None
    ) -> VispyBaseOverlay:
        """Create the visual of `overlay` in plot `cell`."""
        parent = cell.view if isinstance(overlay, CanvasOverlay) else cell.data_scene
        vispy_overlay = create_vispy_overlay(
            overlay=overlay,
            viewer=self.viewer,
            font_info=self._font_info,
            parent=parent,
            **({"layer_filter": layer_filter} if isinstance(overlay, LegendOverlay) else {}),
        )
        vispy_overlay.set_default_font_size(get_settings().appearance.font_size)
        return vispy_overlay

    def _add_overlay_to_visual(self, overlay: Overlay) -> None:
        """Create vispy overlay and add to dictionary of overlay visuals"""
        self._overlay_to_visual[overlay] = [self._create_overlay_visual(overlay, self._cells[0])]
        overlay.events.position.connect(self._update_overlay_canvas_positions)
        overlay.events.visible.connect(self._on_overlay_visibility_change)
        if isinstance(overlay, LegendOverlay):
            overlay.events.outside.connect(self._update_overlay_canvas_positions)
        if isinstance(overlay, CanvasOverlay):
            overlay.events.gridded.connect(self._update_scenegraph)

    def _on_overlay_visibility_change(self, _event: Event | None = None) -> None:
        self._update_gridded_overlays()
        self._update_overlay_canvas_positions()

    def _on_overlay_added(self, event: Event) -> None:
        """Create the visual of an overlay added after the canvas was made."""
        self._add_overlay_to_visual(event.value)
        self._update_gridded_overlays()
        self._request_overlay_positions()

    def _on_overlay_removed(self, event: Event) -> None:
        """Close the visual of a removed overlay."""
        overlay = event.value
        visuals = self._overlay_to_visual.pop(overlay, None)
        if visuals is not None:
            overlay.events.position.disconnect(self._update_overlay_canvas_positions)
            overlay.events.visible.disconnect(self._on_overlay_visibility_change)
            if isinstance(overlay, LegendOverlay):
                overlay.events.outside.disconnect(self._update_overlay_canvas_positions)
            if isinstance(overlay, CanvasOverlay):
                overlay.events.gridded.disconnect(self._update_scenegraph)
            for visual in visuals:
                visual.close()
            self._request_overlay_positions()

    def screenshot(self) -> QImage:
        """Return a QImage based on what is shown in the viewer."""
        return self.native.grabFramebuffer()
