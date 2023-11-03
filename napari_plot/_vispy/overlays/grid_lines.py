"""Grid lines visual"""
import typing as ty

from vispy.scene.visuals import GridLines

from napari._vispy.overlays.base import ViewerOverlayMixin, VispyCanvasOverlay

if ty.TYPE_CHECKING:
    from napari_plot.components.viewer_model import ViewerModel
    from napari_plot.components.gridlines import GridLinesOverlay


class VispyGridLinesOverlay(ViewerOverlayMixin, VispyCanvasOverlay):
    """Grid lines visual."""

    def __init__(self, *, viewer: "ViewerModel", overlay: "GridLinesOverlay", parent=None) -> None:
        super().__init__(node=GridLines(), viewer=viewer, overlay=overlay, parent=parent)

        self.viewer.grid_lines.events.visible.connect(self._on_visible_change)
        self._on_visible_change(None)

    def on_set_visible(self, _evt=None):
        """Toggle state"""
        self.viewer.grid_lines.visible = not self.viewer.grid_lines.visible

    def _on_visible_change(self, _evt=None):
        """Change grid lines visibility"""
        self.node.visible = self.viewer.grid_lines.visible
