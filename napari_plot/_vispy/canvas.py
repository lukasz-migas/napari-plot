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
from vispy.scene.widgets import Grid
from vispy.util.event import Event
from vispy.visuals.transforms import LogTransform

from napari_plot._vispy.camera import VispyCamera
from napari_plot._vispy.overlays.axis import VispyXAxisVisual, VispyYAxisVisual
from napari_plot._vispy.overlays.colorbar import VispyColorBarVisual
from napari_plot._vispy.plot_cell import VispyPlotCell, detach_widget, link_axis
from napari_plot._vispy.tools.drag import VispyDragTool
from napari_plot.components.axis import AxisScale, transform_axis_values
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


class NapariSceneCanvas(SceneCanvas_):
    """Vispy SceneCanvas used to allow for ignoring mouse wheel events with modifiers."""

    view, grid, x_axis, y_axis = None, None, None, None
    # x/y axes of each plot view box, so overlays (e.g. grid lines) can find the axes of the cell they are in
    view_axes: ty.ClassVar[dict] = {}

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

        # connect events
        self.events.add(reset_view=Event, reset_x=Event, reset_y=Event, background_color=Event)

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

    def _on_mouse_double_click(self, event: MouseEvent) -> None:
        """Process mouse double click event"""
        vis = self.visual_at(event.pos)
        # if user double-clicked in the canvas, reset the entire view
        if vis and event.button == 1:
            self.events.reset_view()
        else:
            x, y = event.pos
            x_x, x_y = self.x_axis.node.pos
            y_x, _y_y = self.y_axis.node.pos
            # if clicked on the x-axis, reset x-range
            if x > y_x and y > x_y:
                self.events.reset_x()
            # if clicked on the y-axis, reset y-range
            elif x < x_x:
                self.events.reset_y()


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
        self._cells_grid: Grid | None = None
        self._cells_key: tuple | None = None
        # layers drawn in each plot cell in grid mode; empty outside grid mode
        self._cell_layers: list[list[Layer]] = []
        self._active_cell: VispyPlotCell | None = None
        self.viewer.axis.events.x_scale.connect(self._on_axis_scale_change)
        self.viewer.axis.events.y_scale.connect(self._on_axis_scale_change)

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
        self.x_axis.interactive = True

        # add y-axis widget
        self.y_axis = VispyYAxisVisual(self.viewer, parent=self.view, order=1e6 + 1)
        self.grid.add_widget(self.y_axis.node, row=1, col=0)
        link_axis(self.y_axis, self.view)
        self.y_axis.interactive = True

        # colorbar right of the plot, in the column of the right padding
        padding = self._scene_canvas.padding_x
        self.colorbar = VispyColorBarVisual(self.viewer, self.grid, padding, padding.width_max)

        with self._scene_canvas.modify_context():
            self._scene_canvas.x_axis = self.x_axis
            self._scene_canvas.y_axis = self.y_axis
        self._scene_canvas.view_axes[self.view] = (self.x_axis, self.y_axis)
        self._cells.append(
            VispyPlotCell(self.viewer, self.view, self._data_scene, self.camera, self.x_axis, self.y_axis)
        )
        self._active_cell = self._cells[0]

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
        self._scene_canvas.events.reset_x.connect(self.viewer.reset_x_view)
        self._scene_canvas.events.reset_y.connect(self.viewer.reset_y_view)

        self._scene_canvas.events.mouse_double_click.connect(self._on_mouse_double_click)
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
        self.viewer.canvas.grid.events.connect(self._update_scenegraph)

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
        x_base = 10.0 if self.viewer.axis.x_scale is AxisScale.LOG else 0.0
        y_base = 10.0 if self.viewer.axis.y_scale is AxisScale.LOG else 0.0
        if self.viewer.layers:
            self.viewer._on_update_extent()
            self.viewer.reset_view()
        for cell in self._cells:
            if self.viewer.layers:
                cell.camera.extent = self.viewer.camera.extent
            cell.data_scene.transform = LogTransform((x_base, y_base, 0.0))
            cell.x_axis.node._view_changed()
            cell.y_axis.node._view_changed()
        self._scene_canvas.update()

    def _grid_active(self) -> bool:
        """Whether layers are shown in a grid of plot cells."""
        return bool(self.viewer.canvas.grid.enabled and len(self.viewer.layers))

    def _update_scenegraph(self, _event: Event | None = None) -> None:
        """Lay out the plot cells and put each layer in the cell of its group (a single cell outside grid mode)."""
        if self._grid_active():
            viewboxes = [
                (position, indices)
                for position, indices in self.viewer.canvas.grid.iter_viewboxes(self.viewer.layers)
                if indices
            ]
            self._layout_cells([position for position, _ in viewboxes])
            self._cell_layers = [[self.viewer.layers[index] for index in indices] for _, indices in viewboxes]
            for cell, (_, indices) in zip(self._cells, viewboxes, strict=True):
                for index in indices:
                    layer = self.viewer.layers[index]
                    if layer in self.layer_to_visual:
                        self.layer_to_visual[layer].node.parent = cell.data_scene
                        self._layer_name_visuals[layer].node.parent = cell.view
        else:
            self._layout_single()
            self._cell_layers = []
            for layer, vispy_layer in self.layer_to_visual.items():
                vispy_layer.node.parent = self._data_scene
                self._layer_name_visuals[layer].node.parent = self.view
        self._update_gridded_overlays()
        self._on_interactive()
        self._request_overlay_positions()

    def _layout_cells(self, positions: list[tuple[int, int]]) -> None:
        """Show one plot cell per grid position, reusing existing cells; the first cell is the main view."""
        grid = self.viewer.canvas.grid
        spacing = grid._compute_canvas_spacing(self._scene_canvas.size, self.viewer.layers)
        key = (tuple(positions), spacing)
        if self._cells_grid is not None and key == self._cells_key:
            return
        while len(self._cells) < len(positions):
            self._cells.append(self._create_cell())
        while len(self._cells) > len(positions):
            self._close_cell(self._cells.pop())

        if self._cells_grid is None:
            for widget in self._cells[0].widgets:
                detach_widget(self.grid, widget)
        else:
            detach_widget(self.grid, self._cells_grid)
        # vispy grids are not designed to be rearranged, so the container is rebuilt
        self._cells_grid = Grid(spacing=spacing)
        self.grid.add_widget(self._cells_grid, row=1, col=0, col_span=2)
        for cell, (row, col) in zip(self._cells, positions, strict=True):
            layout = cell.ensure_layout()
            if isinstance(layout.parent, Grid):
                detach_widget(layout.parent, layout)
            self._cells_grid.add_widget(layout, row=row, col=col)
            # adding a grid to another grid replaces its size variables, so its own layout solver must be rebuilt
            layout._need_solver_recreate = True
        self._cells_key = key

    def _layout_single(self) -> None:
        """Close the extra plot cells and put the main view and axes back in the canvas grid."""
        if self._cells_grid is None:
            return
        while len(self._cells) > 1:
            self._close_cell(self._cells.pop())
        main = self._cells[0]
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
        x_base = 10.0 if self.viewer.axis.x_scale is AxisScale.LOG else 0.0
        y_base = 10.0 if self.viewer.axis.y_scale is AxisScale.LOG else 0.0
        cell.data_scene.transform = LogTransform((x_base, y_base, 0.0))
        self._scene_canvas.events.draw.connect(cell.camera.on_draw)
        cell.view.events.resize.connect(self._update_overlay_canvas_positions)
        self._scene_canvas.view_axes[cell.view] = (cell.x_axis, cell.y_axis)
        return cell

    def _close_cell(self, cell: VispyPlotCell) -> None:
        """Disconnect and remove a plot cell created for grid mode."""
        self._scene_canvas.events.draw.disconnect(cell.camera.on_draw)
        cell.view.events.resize.disconnect(self._update_overlay_canvas_positions)
        self._scene_canvas.view_axes.pop(cell.view, None)
        if self._active_cell is cell:
            self._set_active_cell(self._cells[0])
        cell.close()

    def _set_active_cell(self, cell: VispyPlotCell) -> None:
        """Use `cell` for mouse interaction, drawing the drag tool (box zoom, lasso) in it."""
        if cell is self._active_cell:
            return
        self._active_cell = cell
        self.tool._polygon.node.parent = cell.data_scene

    def _update_gridded_overlays(self) -> None:
        """Give gridded overlays one visual per plot cell; other overlays stay in the first cell."""
        for overlay, visuals in self._overlay_to_visual.items():
            gridded = overlay.gridded if isinstance(overlay, CanvasOverlay) else True
            wanted = len(self._cells) if gridded and self._cells_grid is not None else 1
            while len(visuals) > wanted:
                visuals.pop().close()
            for cell in self._cells[len(visuals) : wanted]:
                visuals.append(self._create_overlay_visual(overlay, cell))
        self._update_legend_filters()

    def _update_legend_filters(self) -> None:
        """List in each cell's copy of a gridded legend only the layers drawn in that cell.

        The first cell also lists rows of layers that are in no cell, so they stay visible and clickable. Names are
        looked up when the legend is drawn, so renamed layers keep their cell.
        """
        others = [layer for layers in self._cell_layers[1:] for layer in layers]
        for overlay, visuals in self._overlay_to_visual.items():
            if not isinstance(overlay, LegendOverlay):
                continue
            if len(visuals) == 1:
                visuals[0].set_layer_filter(None)
                continue
            visuals[0].set_layer_filter(lambda name: name not in {layer.name for layer in others})
            for visual, layers in zip(visuals[1:], self._cell_layers[1:], strict=True):
                visual.set_layer_filter(lambda name, layers=layers: name in {layer.name for layer in layers})

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
            for view, visual in enumerate(visuals[: len(self._cells)]):
                if visual.x_size > 0 and visual.y_size > 0:
                    yield overlay, visual, view
        view_indices = {cell.view: index for index, cell in enumerate(self._cells)}
        for layer in self.viewer.layers:
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
        # refresh sizes first; the size-changed event is blocked since the overlays are placed right after
        with self.viewer.canvas.events._overlay_positions_changed.blocker():
            for overlay, visuals in self._overlay_to_visual.items():
                if isinstance(overlay, CanvasOverlay):
                    for visual in visuals:
                        visual._on_position_change()
            for visual in self._layer_name_visuals.values():
                if visual.node.visible:
                    visual._on_position_change()

        tiling = self.viewer.canvas.overlay_tiling
        x_padding, y_padding = tiling.padding
        groups: dict[tuple[int, CanvasPosition], list[VispyCanvasOverlay]] = {}
        for overlay, visual, view in self._get_ordered_visible_canvas_overlays():
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
        self._needs_overlay_position_update = False

    def _update_font_sizes(self, _event: Event | None = None) -> None:
        font_size = get_settings().appearance.font_size
        overlay_visuals = [visual for visuals in self._overlay_to_visual.values() for visual in visuals]
        for visual in (*overlay_visuals, *self.layer_to_visual.values(), *self._layer_name_visuals.values()):
            visual.set_default_font_size(font_size)

    def _disconnect_theme(self) -> None:
        disconnect_events(self.viewer.events, self)
        disconnect_events(self.viewer.canvas.events, self)
        disconnect_events(self.viewer.canvas.overlay_tiling.events, self)
        disconnect_events(self.viewer.canvas.grid.events, self)
        disconnect_events(get_settings().appearance.events, self)
        disconnect_events(self.viewer._overlays.events, self)
        disconnect_events(self.viewer.colorbar.events, self.colorbar)
        disconnect_events(self.viewer.axis.events, self.colorbar)
        for overlay in self._overlay_to_visual:
            overlay.events.position.disconnect(self._update_overlay_canvas_positions)
            overlay.events.visible.disconnect(self._update_overlay_canvas_positions)
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
        if view is None:
            view = self._cell_at(position).view
        position = list(np.asarray(position[:2], dtype=float) - self._view_offset(view))
        transform = view.camera.transform.inverse
        mapped_position = transform.map(position)[:2]
        mapped_position[0] = transform_axis_values(
            mapped_position[0],
            self.viewer.axis.x_scale,
            inverse=True,
        )
        mapped_position[1] = transform_axis_values(
            mapped_position[1],
            self.viewer.axis.y_scale,
            inverse=True,
        )
        position_world_slice = mapped_position[::-1]

        position_world = [0, 0]
        for i, d in enumerate((0, 1)):
            position_world[d] = position_world_slice[i]
        return tuple(position_world)

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
            return

        event.scale = 1.0
        napari_event = NapariMouseEvent(
            event=event,
            view_direction=None,
            up_direction=None,
            camera_zoom=self.viewer.camera.zoom,
            position=self._map_canvas2world(event.pos),
            dims_displayed=[0, 1],
            dims_point=list(self.viewer.dims.point),
            viewbox=(0, 0),
        )

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
        self._process_mouse_event(mouse_double_click_callbacks, event)

    def _on_mouse_move(self, event):
        """Called whenever mouse moves over canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        self._process_mouse_event(mouse_move_callbacks, event)

    def _on_mouse_press(self, event):
        """Called whenever mouse pressed in canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        if event.pos is not None:
            self._set_active_cell(self._cell_at(event.pos))
        self._process_mouse_event(mouse_press_callbacks, event)

    def _on_mouse_release(self, event):
        """Called whenever mouse released in canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        self._process_mouse_event(mouse_release_callbacks, event)

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
        if self._cells_grid is None:
            top_left = self._map_canvas2world([0, 0])
            bottom_right = self._map_canvas2world(self._scene_canvas.size)
        else:
            # the cameras are synchronized, so every cell shows the range of the main view
            offset = self._view_offset(self.view)
            top_left = self._map_canvas2world(offset, self.view)
            bottom_right = self._map_canvas2world(offset + np.asarray(self.view.size), self.view)
        return np.array([top_left, bottom_right])

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
        canvas_corners_world = self._canvas_corners_in_world
        shape_threshold = self._draw_shape_threshold
        for layer in self.viewer.layers:
            if layer.ndim <= 2:
                layer._update_draw(
                    scale_factor=1 / self.viewer.camera.zoom,
                    corner_pixels_displayed=canvas_corners_world[:, -layer.ndim :],
                    shape_threshold=shape_threshold,
                )

    def on_resize(self, event: ResizeEvent) -> None:
        """Called whenever canvas is resized."""
        self.viewer._canvas_size = self.size
        if self._cells_grid is not None:
            # relative grid spacing depends on the canvas size; the cells are only re-laid out when it changes
            spacing = self.viewer.canvas.grid._compute_canvas_spacing(self._scene_canvas.size, self.viewer.layers)
            if spacing != self._cells_key[1]:
                self._update_scenegraph()
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
        # self.viewer.camera.events.angles.connect(vispy_layer._on_camera_move)
        self._reorder_layers()
        self._update_scenegraph()

    def _remove_layer(self, event):
        """When a layer is removed, remove its parent."""
        layer = event.value
        layer.events.visible.disconnect(self._reorder_layers)
        layer.events.visible.disconnect(self._update_scenegraph)
        self._layer_name_visuals.pop(layer).close()
        vispy_layer = self.layer_to_visual[layer]
        vispy_layer.close()
        del vispy_layer
        del self.layer_to_visual[layer]
        self._reorder_layers()
        self._update_scenegraph()

    def _reorder_layers(self):
        """When the list is reordered, propagate changes to draw order."""
        first_visible_found = False
        for i, layer in enumerate(self.viewer.layers):
            vispy_layer = self.layer_to_visual[layer]
            vispy_layer.order = i

            # the bottommost visible layer needs special treatment for blending
            if layer.visible and not first_visible_found:
                vispy_layer.first_visible = True
                first_visible_found = True
            else:
                vispy_layer.first_visible = False
            vispy_layer._on_blending_change()

        self._scene_canvas._draw_order.clear()
        self._scene_canvas.update()

    def _create_overlay_visual(self, overlay: Overlay, cell: VispyPlotCell) -> VispyBaseOverlay:
        """Create the visual of `overlay` in plot `cell`."""
        parent = cell.view if isinstance(overlay, CanvasOverlay) else cell.data_scene
        vispy_overlay = create_vispy_overlay(
            overlay=overlay,
            viewer=self.viewer,
            font_info=self._font_info,
            parent=parent,
        )
        vispy_overlay.set_default_font_size(get_settings().appearance.font_size)
        return vispy_overlay

    def _add_overlay_to_visual(self, overlay: Overlay) -> None:
        """Create vispy overlay and add to dictionary of overlay visuals"""
        self._overlay_to_visual[overlay] = [self._create_overlay_visual(overlay, self._cells[0])]
        overlay.events.position.connect(self._update_overlay_canvas_positions)
        overlay.events.visible.connect(self._update_overlay_canvas_positions)
        if isinstance(overlay, CanvasOverlay):
            overlay.events.gridded.connect(self._update_scenegraph)

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
            overlay.events.visible.disconnect(self._update_overlay_canvas_positions)
            if isinstance(overlay, CanvasOverlay):
                overlay.events.gridded.disconnect(self._update_scenegraph)
            for visual in visuals:
                visual.close()
            self._request_overlay_positions()

    def screenshot(self) -> QImage:
        """Return a QImage based on what is shown in the viewer."""
        return self.native.grabFramebuffer()
