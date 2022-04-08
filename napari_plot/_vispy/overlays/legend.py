"""Legend visual."""
import typing as ty
from weakref import ref

import numpy as np
from vispy.scene.visuals import Text
from vispy.visuals.transforms import STTransform

from ...components._constants import LegendPosition

if ty.TYPE_CHECKING:
    from ...viewer import ViewerModel


class VispyLegendOverlay:
    """Legend overlay."""

    def __init__(self, qt_viewer, viewer: "ViewerModel", parent=None, order=1e6):
        self._ref_qt_viewer = ref(qt_viewer)
        self._viewer = viewer

        self.node = Text(pos=parent.pos, parent=parent, face="Arial")
        self.node.order = order
        self.node.transform = STTransform()
        self.node.font_size = self._viewer.legend.font_size
        self.node.anchors = ("center", "center")

        self._viewer.legend.events.visible.connect(self._on_visible_change)
        self._viewer.legend.events.title.connect(self._on_data_change)
        self._viewer.legend.events.handles.connect(self._on_data_change)
        self._viewer.legend.events.color.connect(self._on_text_change)
        self._viewer.legend.events.bold.connect(self._on_text_change)
        self._viewer.legend.events.font_size.connect(self._on_text_change)
        self._viewer.legend.events.position.connect(self._on_position_change)
        self._viewer.camera.events.zoom.connect(self._on_position_change)

        self._on_visible_change()
        self._on_data_change()
        self._on_text_change()
        self._on_position_change()

    def _on_visible_change(self):
        """Change text visibility."""
        self.node.visible = self._viewer.legend.visible

    def _on_data_change(self):
        """Change text value."""
        text = self._viewer.legend.text
        self.node.text = text
        self.node.color = self._viewer.legend.text_color

        # set position
        x = np.arange(len(text)) * self._viewer.legend.font_size * 2.5
        self.node.pos = np.c_[np.zeros_like(x), x]

    def _on_text_change(self):
        """Update text size and color."""
        self.node.font_size = self._viewer.legend.font_size
        self.node.bold = self._viewer.legend.bold
        self.node.color = self._viewer.legend.text_color

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

        if position == LegendPosition.TOP_LEFT:
            transform = [x_offset, y_offset, 0, 0]
            anchors = ("left", "bottom")
        elif position == LegendPosition.TOP_RIGHT:
            transform = [canvas_size[0] - x_offset, y_offset, 0, 0]
            anchors = ("right", "bottom")
        elif position == LegendPosition.TOP_CENTER:
            transform = [canvas_size[0] // 2, y_offset, 0, 0]
            anchors = ("center", "bottom")
        elif position == LegendPosition.BOTTOM_RIGHT:
            transform = [canvas_size[0] - x_offset, canvas_size[1] - y_offset, 0, 0]
            anchors = ("right", "top")
        elif position == LegendPosition.BOTTOM_LEFT:
            transform = [x_offset, canvas_size[1] - y_offset, 0, 0]
            anchors = ("left", "top")
        elif position == LegendPosition.BOTTOM_CENTER:
            transform = [canvas_size[0] // 2, canvas_size[1] - y_offset, 0, 0]
            anchors = ("center", "top")
        else:
            raise ValueError(f"Position {position} is not recognized.")

        self.node.transform.translate = transform
        if self.node.anchors != anchors:
            self.node.anchors = anchors
