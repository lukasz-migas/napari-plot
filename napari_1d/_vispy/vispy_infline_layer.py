"""Line layer"""

from napari._vispy.layers.base import VispyBaseLayer
from vispy.scene.visuals import Compound, Line, Mesh

from ..layers.infline import InfLine
from ..layers.utilities import make_infinite_color, make_infinite_line


class VispyInfLineLayer(VispyBaseLayer):
    """Infinite region layer"""

    def __init__(self, layer: InfLine):
        # Create a compound visual with the following four sub-visuals:
        # Lines: The actual infinite lines
        # Lines: Highlight of the selected infinite line using different color and width
        # Mesh: Used to draw selection box in the canvas.
        node = Compound([Line(), Line(), Mesh()])
        super().__init__(layer, node)

        self.layer.events.color.connect(self._on_appearance_change)
        self.layer.events.width.connect(self._on_width_change)

        self.reset()
        self._on_data_change()

    def _on_appearance_change(self, _event=None):
        """Change the appearance of the data"""
        self.node._subvisuals[0].set_data(color=make_infinite_color(self.layer.color))
        self.node.update()

    def _on_width_change(self, _event=None):
        """Change the appearance of the data"""
        self.node._subvisuals[0].set_data(width=self.layer.width)
        self.node.update()

    def _on_data_change(self, _event=None):
        """Set data"""
        pos, connect, color = make_infinite_line(self.layer.data, self.layer.orientations, self.layer.color)
        # primary visualisation of the infinite lines
        self.node._subvisuals[0].set_data(
            pos=pos,
            connect=connect,
            color=color,
            width=self.layer.width,
        )
        self.node.update()

    def _on_highlight_change(self, _event=None):
        """Set highlights."""
        # pos, connect, color = make_infinite_line(self.layer.data, self.layer.orientations, self.layer.color)
        # highlights of the infinite lines
        # self.node._subvisuals[1].set_data(
        #     pos=pos,
        #     connect=connect,
        #     color="#0000FF",  # color,
        #     width=self.layer.width * 2,
        # )
