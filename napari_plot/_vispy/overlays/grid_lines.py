"""Grid lines visual"""

import typing as ty

from napari._vispy.overlays.base import ViewerOverlayMixin, VispyCanvasOverlay
from vispy.scene.visuals import GridLines

if ty.TYPE_CHECKING:
    from napari._vispy.utils.qt_font import FontInfo

    from napari_plot.components.grid_lines import GridLinesOverlay
    from napari_plot.components.viewer_model import ViewerModel


class VispyGridLinesOverlay(ViewerOverlayMixin, VispyCanvasOverlay):
    """Grid lines visual."""

    def __init__(
        self,
        *,
        viewer: "ViewerModel",
        overlay: "GridLinesOverlay",
        font_info: "FontInfo",
        parent=None,
    ) -> None:
        super().__init__(node=GridLines(), viewer=viewer, overlay=overlay, font_info=font_info, parent=parent)

        self.viewer.grid_lines.events.visible.connect(self._on_visible_change)
        self._on_visible_change(None)

    def on_set_visible(self, _evt=None):
        """Toggle state"""
        self.viewer.grid_lines.visible = not self.viewer.grid_lines.visible

    def _on_visible_change(self, _evt=None):
        """Change grid lines visibility"""
        self.node.visible = self.viewer.grid_lines.visible
