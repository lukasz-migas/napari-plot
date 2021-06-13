"""Span visual - based on the `Region` layer"""
# Third-party imports
from typing import TYPE_CHECKING

from vispy.scene.visuals import LinearRegion

if TYPE_CHECKING:
    from ..components.viewer_model import ViewerModel


class VispySpanVisual:
    """Infinite span visual user to select region of interest in 1d."""

    def __init__(self, viewer: "ViewerModel", parent=None, order=1e6):
        self._viewer = viewer

        self.node = LinearRegion(vertical=viewer.span.orientation)
        self.node.order = order
        if parent:
            parent.add(self.node)

        self._viewer.span.events.visible.connect(self._on_visible_change)
        self._viewer.span.events.opacity.connect(self._on_opacity_change)
        self._viewer.span.events.color.connect(self._on_color_change)
        self._viewer.span.events.position.connect(self._on_data_change)

        self._on_visible_change()
        self._on_color_change()
        self._on_opacity_change()
        self._on_data_change()

    def _on_visible_change(self, _evt=None):
        """Change span visibility"""
        self.node.visible = self._viewer.span.visible

    def _on_opacity_change(self, _evt=None):
        """Change span visibility"""
        self.node.opacity = self._viewer.span.opacity

    def _on_color_change(self, _event=None):
        """Change the appearance of the data"""
        self.node.set_data(color=self._viewer.span.color)
        self.node.update()

    def _on_data_change(self, _event=None):
        """Set data"""
        self.node.set_data(self._viewer.span.position, color=self._viewer.span.color)
        self.node.update()
