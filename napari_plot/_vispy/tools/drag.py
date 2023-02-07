"""Interaction tool."""
import typing as ty

from napari_plot._vispy.tools.polygon import VispyPolygonVisual
from napari_plot.components.dragtool import BOX_SELECT_TOOLS, BOX_ZOOM_TOOLS, DragMode

if ty.TYPE_CHECKING:
    from napari_plot.components.viewer_model import ViewerModel


class VispyDragTool:
    """Interaction tool."""

    def __init__(self, viewer: "ViewerModel", view, order=1e6):
        self._view = view
        self._viewer = viewer

        # initialize each Tool
        # Polygon can be used by both `BoxTool` and `PolygonTool`
        self._polygon = VispyPolygonVisual(viewer, parent=view, order=order)
        self.tool = self._polygon

        self._viewer.drag_tool.events.active.connect(self._on_tool_change)
        self._viewer.drag_tool.events.tool.connect(self._on_tool_change)

    def _on_tool_change(self, _evt=None):
        """Change currently selected tool."""
        if self._viewer.drag_tool.active in BOX_ZOOM_TOOLS or self._viewer.drag_tool.active in BOX_SELECT_TOOLS:
            self.tool = self._polygon
        elif self._viewer.drag_tool.active == DragMode.LASSO:
            self.tool = self._polygon
        elif self._viewer.drag_tool.active == DragMode.POLYGON:
            self.tool = self._polygon
        elif self._viewer.drag_tool.active == DragMode.NONE:
            self.tool = None
