"""Override text visual to fix label cropping"""


from napari._vispy.overlays.text import CanvasPosition, VispyTextOverlay as _VispyTextOverlay


class VispyTextOverlay(_VispyTextOverlay):
    """Overwrite text position"""

    def __init__(self, *, viewer, overlay, parent=None) -> None:
        # self._ref_qt_viewer = ref(qt_viewer)
        super().__init__(viewer=viewer, overlay=overlay, parent=parent)

    def _on_position_change(self, event=None):
        """Change position of text visual.

        This is necessary to account for the offsets caused by the x/y-axis offsets.
        """
        position = self.viewer.text_overlay.position
        x_offset, y_offset = 10, 5
        if not self.node.canvas:
            super()._on_position_change(event)
        else:
            canvas_size = list(self.node.canvas.size)
            canvas_offset = self.node.parent.pos
            canvas_size[1] -= canvas_offset[1] + 50
            canvas_size[0] -= canvas_offset[0]  # - 20

            if position == CanvasPosition.TOP_LEFT:
                transform = [x_offset, y_offset, 0, 0]
                anchors = ("left", "bottom")
            elif position == CanvasPosition.TOP_RIGHT:
                transform = [canvas_size[0] - x_offset, y_offset, 0, 0]
                anchors = ("right", "bottom")
            elif position == CanvasPosition.TOP_CENTER:
                transform = [canvas_size[0] // 2, y_offset, 0, 0]
                anchors = ("center", "bottom")
            elif position == CanvasPosition.BOTTOM_RIGHT:
                transform = [canvas_size[0] - x_offset, canvas_size[1] - y_offset, 0, 0]
                anchors = ("right", "top")
            elif position == CanvasPosition.BOTTOM_LEFT:
                transform = [x_offset, canvas_size[1] - y_offset, 0, 0]
                anchors = ("left", "top")
            elif position == CanvasPosition.BOTTOM_CENTER:
                transform = [canvas_size[0] // 2, canvas_size[1] - y_offset, 0, 0]
                anchors = ("center", "top")
            else:
                raise ValueError("Position {position} is not recognized.")

            self.node.transform.translate = transform
            if self.node.anchors != anchors:
                self.node.anchors = anchors
