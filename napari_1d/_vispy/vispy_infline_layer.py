"""Line layer"""
import numpy as np
from napari._vispy.layers.base import VispyBaseLayer
from vispy.scene.visuals import Compound, Line

from ..layers.infline import InfLine

LINE_MAIN = 0
LINE_BOX = 1
LINE_HIGHLIGHT = 2


class VispyInfLineLayer(VispyBaseLayer):
    """Infinite region layer"""

    def __init__(self, layer: InfLine):
        # Create a compound visual with the following four sub-visuals:
        # Line: The actual infinite lines
        # Line: Used to draw selection box in the canvas.
        # Line: Highlight of the selected infinite line using different color and width
        node = Compound([Line(), Line(), Line()])
        super().__init__(layer, node)

        self.layer.events.color.connect(self._on_appearance_change)
        self.layer.events.width.connect(self._on_width_change)
        self.layer.events.highlight.connect(self._on_highlight_change)

        self.reset()
        self._on_data_change()

    def _on_appearance_change(self, _event=None):
        """Change the appearance of the data"""
        self.node._subvisuals[LINE_MAIN].set_data(color=self.layer._data_view.get_display_color())
        self.node.update()

    def _on_width_change(self, _event=None):
        """Change the appearance of the data"""
        self.node._subvisuals[LINE_MAIN].set_data(width=self.layer.width)
        self.node.update()

    def _on_data_change(self, _event=None):
        """Set data"""
        pos, connect, color = self.layer._data_view.get_display_lines()
        if len(pos) == 0:
            color = (0, 0, 0, 0)
        # primary visualisation of the infinite lines
        self.node._subvisuals[LINE_MAIN].set_data(
            pos=pos,
            connect=connect,
            color=color,
            width=self.layer.width,
        )
        self.node.update()

    def _on_highlight_change(self, _event=None):
        """Highlight."""
        pos, connect, _ = self.layer._data_view.get_display_lines(indices=self.layer.selected_data)
        # primary visualisation of the infinite lines
        self.node._subvisuals[LINE_HIGHLIGHT].set_data(
            pos=pos,
            connect=connect,
            color=self.layer._highlight_color,
            width=self.layer.width * 2,
        )

        # Compute the location and properties of the vertices and box that
        # need to get rendered
        edge_color, pos, width = self.layer._compute_box()

        # add region edges
        if pos is None or len(pos) == 0:
            pos = np.zeros((1, self.layer._ndisplay))
            width = 0
        self.node._subvisuals[LINE_BOX].set_data(pos=pos, color=edge_color, width=width)
        self.node.update()
