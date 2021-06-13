"""Override text visual to fix label cropping"""
from napari._vispy.vispy_text_visual import TextOverlayPosition
from napari._vispy.vispy_text_visual import VispyTextVisual as _VispyTextVisual
from napari._vispy.vispy_text_visual import trans


class VispyTextVisual(_VispyTextVisual):
    """Overwrite text position"""

    def __init__(self, qt_viewer, viewer, parent=None, order=1e6):
        self._qt_viewer = qt_viewer
        super().__init__(viewer, parent, order)

    def _on_position_change(self, event):
        """Change position of text visual."""
        position = self._viewer.text_overlay.position
        x_offset, y_offset = 10, 5
        canvas_size = list(self.node.canvas.size)
        canvas_offset = self._qt_viewer.pos_offset
        if canvas_offset:
            canvas_size[0] -= canvas_offset[0] + 10
            canvas_size[1] -= canvas_offset[1]

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
            raise ValueError(trans._("Position {position} is not recognized.", position=position))

        self.node.transform.translate = transform
        if self.node.anchors != anchors:
            self.node.anchors = anchors
