"""Override text visual to fix label cropping"""
from weakref import ref

from napari._vispy.overlays.text import TextOverlayPosition
from napari._vispy.overlays.text import VispyTextOverlay as _VispyTextVisual


class VispyTextVisual(_VispyTextVisual):
    """Overwrite text position"""

    def __init__(self, qt_viewer, viewer, parent=None, order=1e6):
        self._ref_qt_viewer = ref(qt_viewer)
        super().__init__(viewer, parent, order)

    def _on_position_change(self, event=None):
        """Change position of text visual.

        This is necessary to account for the offsets caused by the x/y-axis offsets.
        """
        position = self._viewer.text_overlay.position
        x_offset, y_offset = 10, 5
        canvas_size = list(self.node.canvas.size)
        canvas_offset = self._ref_qt_viewer().view.pos
        canvas_size[1] -= canvas_offset[1] + 50
        canvas_size[0] -= canvas_offset[0]  # - 20

        if position == TextOverlayPosition.TOP_LEFT:
            transform = [x_offset, y_offset, 0, 0]
            anchors = ("left", "bottom")
        elif position == TextOverlayPosition.TOP_RIGHT:
            transform = [canvas_size[0] - x_offset, y_offset, 0, 0]
            anchors = ("right", "bottom")
        elif position == TextOverlayPosition.TOP_CENTER:
            transform = [canvas_size[0] // 2, y_offset, 0, 0]
            anchors = ("center", "bottom")
        elif position == TextOverlayPosition.BOTTOM_RIGHT:
            transform = [
                canvas_size[0] - x_offset,
                canvas_size[1] - y_offset,
                0,
                0,
            ]
            anchors = ("right", "top")
        elif position == TextOverlayPosition.BOTTOM_LEFT:
            transform = [x_offset, canvas_size[1] - y_offset, 0, 0]
            anchors = ("left", "top")
        elif position == TextOverlayPosition.BOTTOM_CENTER:
            transform = [canvas_size[0] // 2, canvas_size[1] - y_offset, 0, 0]
            anchors = ("center", "top")
        else:
            raise ValueError("Position {position} is not recognized.")

        self.node.transform.translate = transform
        if self.node.anchors != anchors:
            self.node.anchors = anchors
