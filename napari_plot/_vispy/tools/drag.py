"""Interaction tool."""
import typing as ty

from ...components.dragtool import BOX_INTERACTIVE_TOOL, DragMode
from .box import VispyBoxVisual

if ty.TYPE_CHECKING:
    from ...components.viewer_model import ViewerModel


class VispyDragTool:
    """Interaction tool."""

    def __init__(self, viewer: "ViewerModel", view, order=1e6):
        self._view = view
        self._viewer = viewer

        # initialize each Tool
        self._box = VispyBoxVisual(viewer, parent=view, order=order)
        self._lasso = None
        self._polygon = None

        self.tool = self._box

        self._viewer.drag_tool.events.active.connect(self._on_tool_change)
        self._viewer.drag_tool.events.tool.connect(self._on_tool_change)

    def _on_tool_change(self, _evt=None):
        """Change currently selected tool."""
        if self._viewer.drag_tool.active in BOX_INTERACTIVE_TOOL:
            self.tool = self._box
        elif self._viewer.drag_tool.active == DragMode.LASSO:
            self.tool = self._lasso
        elif self._viewer.drag_tool.active == DragMode.POLYGON:
            self.tool = self._polygon
        elif self._viewer.drag_tool.active == DragMode.NONE:
            self.tool = None
