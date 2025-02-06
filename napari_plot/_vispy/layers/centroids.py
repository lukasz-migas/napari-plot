"""Centroids layer"""

import typing as ty

from napari._vispy.layers.base import VispyBaseLayer

from napari_plot._vispy.visuals.centroids import CentroidsVisual
from napari_plot.layers.centroids._centroids_utils import (
    make_centroids,
    make_centroids_color,
)

if ty.TYPE_CHECKING:
    from napari_plot.layers import Centroids


class VispyCentroidsLayer(VispyBaseLayer):
    """Centroids layer"""

    layer: "Centroids"
    node: CentroidsVisual

    def __init__(self, layer: "Centroids"):
        node = CentroidsVisual()
        super().__init__(layer, node)

        self.layer.events.color.connect(self._on_appearance_change)
        self.layer.events.width.connect(self._on_appearance_change)
        self.layer.events.method.connect(self._on_method_change)
        self.layer.events.highlight.connect(self._on_highlight_change)

        self.reset()
        self._on_data_change()

    def _on_highlight_change(self, _event=None):
        """Mark region of interest on the visual"""

    def _on_appearance_change(self, _event=None):
        """Change the appearance of the data"""
        colors = make_centroids_color(self.layer.color)
        self.node.set_data(color=colors, width=self.layer.width)

    def _on_data_change(self, _event=None):
        """Set data"""
        pos, colors = make_centroids(self.layer.data, self.layer.color, self.layer.orientation)
        self.node.set_data(
            pos=pos,
            connect="segments",
            color=colors,
            width=self.layer.width,
        )

    def _on_method_change(self, _event=None):
        self.node.method = self.layer.method
