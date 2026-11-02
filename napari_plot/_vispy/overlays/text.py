"""Override text visual to fix label cropping"""

from napari._vispy.overlays.text import VispyTextOverlay as _VispyTextOverlay


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

        if "left" in position:
            x = x_offset
        elif "right" in position:
            x = canvas_size[0] - self.x_size - x_offset
        else:
            x = (canvas_size[0] - self.x_size) / 2
        if "top" in position:
            y = y_offset
        elif "bottom" in position:
            y = canvas_size[1] - self.y_size - y_offset
        else:
            y = (canvas_size[1] - self.y_size) / 2
        self.node.transform.translate = [max(0, x), max(0, y), 0, 0]
        self._on_box_change()
