"""Plot cell: one plot area of the canvas, used to show layer groups side by side in grid mode."""

from __future__ import annotations

import typing as ty
from functools import partial

import numpy as np
from napari.utils.events import disconnect_events
from vispy.scene import Node
from vispy.scene.widgets import Grid

from napari_plot._vispy.camera import VispyCamera
from napari_plot._vispy.components.axis_transform import axis_transform
from napari_plot._vispy.overlays.axis import VispyXAxisVisual, VispyYAxisVisual

if ty.TYPE_CHECKING:
    from collections.abc import Sequence

    from napari.layers import Layer
    from vispy.scene import ViewBox, Widget
    from vispy.scene.events import SceneMouseEvent

    from napari_plot.components.canvas import PlotGridCell
    from napari_plot.components.viewer_model import ViewerModel

AXIS_ORDER = 1e6 + 1


def detach_widget(grid: Grid, widget: Widget) -> None:
    """Remove `widget` from `grid`, including the bookkeeping that `Grid.remove_widget` leaves behind."""
    grid.remove_widget(widget)
    if widget in grid._widgets:
        grid._widgets.remove(widget)
    for row in grid._cells.values():
        for col in [col for col, cell_widget in row.items() if cell_widget is widget]:
            del row[col]
    widget.parent = None


def link_axis(axis: VispyXAxisVisual | VispyYAxisVisual, view: ViewBox) -> None:
    """Make `axis` follow the camera, size and position of `view`."""
    axis.node.link_view(view)
    axis.node.events.resize.connect(axis.node._view_changed)
    # the ticks depend on where the axis sits relative to the view; grid relayouts move both without a resize or
    # camera change. Moving a widget changes its transform in place, which `Node.events.transform_change` misses.
    for node in (axis.node, view):
        node.transform.changed.connect(axis.node._view_changed)
    axis._on_max_size_change()
    # the whole axis area accepts the mouse, so it can be dragged to pan, or scrolled to zoom, along the axis
    axis.node.interactive = True
    handler = partial(_on_axis_mouse, axis, view)
    for event_name in ("mouse_press", "mouse_move", "mouse_release", "mouse_wheel"):
        getattr(axis.node.events, event_name).connect(handler)


def _on_axis_mouse(axis: VispyXAxisVisual | VispyYAxisVisual, view: ViewBox, event: SceneMouseEvent) -> None:
    """Pan or zoom `view` along `axis` only.

    Dragging the axis with the right mouse button pans; the mouse wheel zooms about the value under the mouse.
    Modified clicks are ignored; the canvas already drops modified wheel events.
    """
    index = 0 if isinstance(axis, VispyXAxisVisual) else 1
    if event.type == "mouse_wheel":
        if not (axis._viewer.camera.mouse_zoom and view.interactive):
            return
        camera = view.camera
        # the same zoom step as scrolling in the plot area, applied to one axis
        factor = [1.0, 1.0]
        factor[index] = (1 + camera.zoom_factor) ** (-event.mouse_event.delta[1] * 30)
        center = view.scene.node_transform(view.canvas.central_widget).imap(event.mouse_event.pos[:2])
        camera.zoom(factor, center[:2])
        event.handled = True
        return
    if event.type == "mouse_press":
        # accepting the press makes vispy send the rest of the drag to this axis only, so the plot camera does not
        # pan both axes when the mouse leaves the axis area
        event.handled = (
            event.button == 2 and not event.mouse_event.modifiers and axis._viewer.camera.mouse_pan and view.interactive
        )
        return
    if event.type != "mouse_move" or event.press_event is None or 2 not in event.buttons:
        return
    # canvas pixels to scene units; the offset of the view cancels out in the difference
    transform = view.camera.transform
    previous = transform.imap(np.asarray(event.mouse_event.last_event.pos[:2], dtype=float))
    current = transform.imap(np.asarray(event.mouse_event.pos[:2], dtype=float))
    delta = np.zeros(2)
    delta[index] = previous[index] - current[index]
    view.camera.pan(delta)
    event.handled = True


class VispyPlotCell:
    """Plot area with its own view box, data scene, camera and x/y axes.

    The canvas always has one cell, built from its main view and axes. In grid mode each layer group gets a cell,
    with shared or independent limits along each axis.
    In grid mode each cell is laid out in its own small grid: the y-axis left of the view and the x-axis below it.
    """

    def __init__(
        self,
        viewer: ViewerModel,
        view: ViewBox,
        data_scene: Node,
        camera: VispyCamera,
        x_axis: VispyXAxisVisual,
        y_axis: VispyYAxisVisual,
        layout: Grid | None = None,
    ) -> None:
        self.viewer = viewer
        self.view = view
        self.data_scene = data_scene
        self.camera = camera
        self.x_axis = x_axis
        self.y_axis = y_axis
        self.layout = layout
        self.position = (0, 0)
        self._axis_transform_key: tuple | None = None

    @property
    def position(self) -> tuple[int, int]:
        """Grid position (row, column) of this cell."""
        return self.camera.position or (0, 0)

    @position.setter
    def position(self, position: tuple[int, int]) -> None:
        self.camera.position = position

    @classmethod
    def create(cls, viewer: ViewerModel) -> VispyPlotCell:
        """Create a new cell with its own layout, view, camera and axes."""
        layout = Grid(spacing=0)
        view = layout.add_view(row=0, col=1)
        data_scene = Node(parent=view.scene)
        camera = VispyCamera(view, viewer.camera, viewer, follow_model=True)
        x_axis = VispyXAxisVisual(viewer, parent=view, order=AXIS_ORDER)
        layout.add_widget(x_axis.node, row=1, col=1)
        y_axis = VispyYAxisVisual(viewer, parent=view, order=AXIS_ORDER)
        layout.add_widget(y_axis.node, row=0, col=0)
        link_axis(x_axis, view)
        link_axis(y_axis, view)
        return cls(viewer, view, data_scene, camera, x_axis, y_axis, layout)

    @property
    def widgets(self) -> tuple[Widget, Widget, Widget]:
        """The y-axis, view and x-axis widgets."""
        return self.y_axis.node, self.view, self.x_axis.node

    def ensure_layout(self) -> Grid:
        """Return the cell layout, moving the axes and view into it when they are elsewhere."""
        if self.layout is None:
            self.layout = Grid(spacing=0)
        # the view goes first: the grid ties row and column sizes to the first widget it lists in each of them
        y_axis, view, x_axis = self.widgets
        for widget, (row, col) in ((view, (0, 1)), (x_axis, (1, 1)), (y_axis, (0, 0))):
            if widget.parent is not self.layout:
                if isinstance(widget.parent, Grid):
                    detach_widget(widget.parent, widget)
                self.layout.add_widget(widget, row=row, col=col)
        return self.layout

    def close(self) -> None:
        """Disconnect the camera and axes from the viewer and remove the cell from the scene."""
        disconnect_events(self.viewer.camera.events, self.camera)
        for axis in (self.x_axis, self.y_axis):
            disconnect_events(self.viewer.axis.events, axis)
            self.viewer.events.theme.disconnect(axis._on_color_change)
        if self.layout is not None and isinstance(self.layout.parent, Grid):
            detach_widget(self.layout.parent, self.layout)
        # Detach children before the cell's scene is collected so VisPy can remove its clipper.
        for child in self.data_scene.children:
            child.parent = None
        self.view.parent = None

    def configure_axes(
        self,
        model: PlotGridCell | None,
        layers: Sequence[Layer] | None,
        shared: tuple[bool, bool],
        *,
        reset: tuple[bool, bool] = (False, False),
        labels_visible: bool = True,
        own_formatters: tuple[bool, bool] = (False, False),
    ) -> None:
        """Apply the grid cell's overrides and synchronize its transforms.

        ``own_formatters`` marks the (x, y) axes whose tick formatter comes only from the cell model (``None`` is the
        default format), e.g. the value axes of joint marginals, instead of falling back to the viewer's axis.
        """
        self.camera.configure_cell(model, layers, shared, reset=reset)
        axis = self.viewer.axis
        key = (self.camera.axis_scale("x"), self.camera.axis_scale("y"), axis.x_power, axis.y_power)
        if key != self._axis_transform_key:
            self._axis_transform_key = key
            self.data_scene.transform = axis_transform(*key)
        for visual, own_formatter in zip((self.x_axis, self.y_axis), own_formatters, strict=True):
            visual.configure_cell(model, label_visible=labels_visible, own_formatter=own_formatter)
            visual.node._view_changed()
