"""Plot cell: one plot area of the canvas, used to show layer groups side by side in grid mode."""

from __future__ import annotations

import typing as ty

from napari.utils.events import disconnect_events
from vispy.scene import Node
from vispy.scene.widgets import Grid

from napari_plot._vispy.camera import VispyCamera
from napari_plot._vispy.overlays.axis import VispyXAxisVisual, VispyYAxisVisual

if ty.TYPE_CHECKING:
    from vispy.scene import ViewBox, Widget

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


class VispyPlotCell:
    """Plot area with its own view box, data scene, camera and x/y axes.

    The canvas always has one cell, built from its main view and axes. In grid mode, each group of layers gets a
    cell; the cameras of all cells follow the single camera model, so every cell shows the same x/y range.
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
        if self.layout is not None and isinstance(self.layout.parent, Grid):
            detach_widget(self.layout.parent, self.layout)
        self.view.parent = None
