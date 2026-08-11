"""Override text visual to fix label cropping"""

from napari._vispy.overlays.text import CanvasPosition, VispyTextOverlay as _VispyTextOverlay


class VispyTextOverlay(_VispyTextOverlay):
    """Overwrite text position"""

    def __init__(self, *, viewer, overlay, font_info, parent=None) -> None:
        super().__init__(viewer=viewer, overlay=overlay, font_info=font_info, parent=parent)

    def _on_position_change(self, event=None):
        """Change position of text visual.

        This is necessary to account for the offsets caused by the x/y-axis offsets.
        """
        super()._on_position_change(event)
        if not self.node.canvas:
            return

        position = self.overlay.position
        x_offset, y_offset = 10, 5
        canvas_size = list(self.node.canvas.size)
        canvas_offset = self.node.parent.pos
        canvas_size[1] -= canvas_offset[1] + 50
        canvas_size[0] -= canvas_offset[0]

        if position == CanvasPosition.TOP_LEFT:
            transform = [x_offset, y_offset, 0, 0]
        elif position == CanvasPosition.TOP_RIGHT:
            transform = [canvas_size[0] - self.x_size - x_offset, y_offset, 0, 0]
        elif position == CanvasPosition.TOP_CENTER:
            transform = [(canvas_size[0] - self.x_size) / 2, y_offset, 0, 0]
        elif position == CanvasPosition.BOTTOM_RIGHT:
            transform = [
                canvas_size[0] - self.x_size - x_offset,
                canvas_size[1] - self.y_size - y_offset,
                0,
                0,
            ]
        elif position == CanvasPosition.BOTTOM_LEFT:
            transform = [x_offset, canvas_size[1] - self.y_size - y_offset, 0, 0]
        elif position == CanvasPosition.BOTTOM_CENTER:
            transform = [
                (canvas_size[0] - self.x_size) / 2,
                canvas_size[1] - self.y_size - y_offset,
                0,
                0,
            ]
        else:
            raise ValueError(f"Position {position} is not recognized.")

        self.node.transform.translate = transform
        self._on_box_change()
