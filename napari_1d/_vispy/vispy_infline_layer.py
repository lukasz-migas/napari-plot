"""Line layer"""
import numpy as np
from napari._vispy.vispy_base_layer import VispyBaseLayer
from vispy.scene.visuals import Compound, Line

from ..layers.infline import InfLine
from ..layers.infline._infline_constants import Orientation


def make_infinite_line(data: np.ndarray, orientations: np.ndarray, colors):
    """Create all elements required to create infinite lines."""
    assert (
        len(data) == len(orientations) == len(colors)
    ), "The number of points must match the number of orientations and colors."
    pos, connect, _colors = [], [], []
    min_val, max_val = np.iinfo(np.int64).min, np.iinfo(np.int64).max
    i = 0
    for (val, orientation, color) in zip(data, orientations, colors):
        if orientation == Orientation.VERTICAL:
            _pos = [[val, min_val], [val, max_val]]
        else:
            _pos = [[min_val, val], [max_val, val]]

        _colors.extend([color, color])
        pos.extend(_pos)
        connect.append([i, i + 1])
        i += 2
    return np.asarray(pos, dtype=object), np.asarray(connect, dtype=object), np.asarray(_colors, dtype=object)


class VispyInfLineLayer(VispyBaseLayer):
    """Infinite region layer"""

    def __init__(self, layer: InfLine):
        # Create a compound visual with the following four sub-visuals:
        # Lines: The actual infinite lines
        # Lines: The lines of the interaction box used for highlights
        node = Compound([Line(), Line()])
        super().__init__(layer, node)

        self.layer.events.color.connect(self._on_appearance_change)
        self.layer.events.width.connect(self._on_width_change)

        self._reset_base()
        self._on_data_change()

    def _on_appearance_change(self, _event=None):
        """Change the appearance of the data"""
        self.node._subvisuals[0].set_data(color=self.layer.color)
        self.node.update()

    def _on_width_change(self, _event=None):
        """Change the appearance of the data"""
        self.node._subvisuals[0].set_data(width=self.layer.width)
        self.node.update()

    def _on_data_change(self, _event=None):
        """Set data"""
        pos, connect, color = make_infinite_line(self.layer.data, self.layer.orientations, self.layer.color)
        self.node._subvisuals[0].set_data(
            pos=pos,
            connect=connect,
            color=color,
            width=self.layer.width,
        )
        self.node.update()

    def _on_highlight_change(self, _event=None):
        """Set highlights."""
