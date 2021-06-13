"""Grid lines visual"""
from vispy.scene.visuals import GridLines as GridLinesNode


class VispyGridLinesVisual:
    """Grid lines visual."""

    def __init__(self, viewer, parent=None, order=1e6):
        self._viewer = viewer

        self.node = GridLinesNode()
        self.node.order = order
        parent.add(self.node)

        self._viewer.grid_lines.events.visible.connect(self._on_visible_change)

        self._on_visible_change(None)

    def on_set_visible(self, _evt=None):
        """Toggle state"""
        self._viewer.grid_lines.visible = not self._viewer.grid_lines.visible

    def _on_visible_change(self, _evt=None):
        """Change grid lines visibility"""
        self.node.visible = self._viewer.grid_lines.visible
