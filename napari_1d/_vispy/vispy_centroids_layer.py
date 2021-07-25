"""Centroids layer"""
from typing import TYPE_CHECKING

from napari._vispy.vispy_base_layer import VispyBaseLayer
from vispy.scene.visuals import Compound
from vispy.scene.visuals import Line as LineVisual
from vispy.scene.visuals import Markers

from .utils import make_centroids

if TYPE_CHECKING:
    from ..layers import Line


class VispyCentroidsLayer(VispyBaseLayer):
    """Centroids layer"""

    def __init__(self, layer: "Line"):
        node = Compound([LineVisual(), Markers()])
        super().__init__(layer, node)

        self.layer.events.color.connect(self._on_appearance_change)
        self.layer.events.width.connect(self._on_appearance_change)
        self.layer.events.method.connect(self._on_method_change)
        self.layer.events.highlight.connect(self._on_highlight_change)

        self._reset_base()
        self._on_data_change()

    def _on_highlight_change(self, _event=None):
        """Mark region of interest on the visual"""

    def _on_appearance_change(self, _event=None):
        """Change the appearance of the data"""
        self.node._subvisuals[0].set_data(color=self.layer.color, width=self.layer.width)

    def _on_data_change(self, _event=None):
        """Set data"""
        self.node._subvisuals[0].set_data(
            make_centroids(self.layer.data),
            connect="segments",
            color=self.layer.color,
            width=self.layer.width,
        )

    def _on_method_change(self, _event=None):
        self.node._subvisuals[0].method = self.layer.method
