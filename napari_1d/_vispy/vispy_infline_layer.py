"""Line layer"""
from typing import TYPE_CHECKING

from napari._vispy.vispy_base_layer import VispyBaseLayer
from vispy.scene.visuals import InfiniteLine

if TYPE_CHECKING:
    from ..layers import InfLine


class VispyInfLineLayer(VispyBaseLayer):
    """Infinite region layer"""

    def __init__(self, layer: "InfLine"):
        node = InfiniteLine(vertical=layer.orientation == "vertical")
        super().__init__(layer, node)

        self.layer.events.color.connect(self._on_appearance_change)

        self._reset_base()
        self._on_data_change()

    def _on_appearance_change(self, _event=None):
        """Change the appearance of the data"""
        self.node.set_data(color=self.layer.color)
        self.node.update()

    def _on_data_change(self, _event=None):
        """Set data"""
        self.node.set_data(self.layer.data, color=self.layer.color)
        self.node.update()
