"""Line layer"""

import typing as ty

from napari._vispy.layers.base import VispyBaseLayer

from napari_plot._vispy.visuals.line import LineVisual

if ty.TYPE_CHECKING:
    from napari_plot.layers import Line


class VispyLineLayer(VispyBaseLayer):
    """Line layer."""

    layer: "Line"
    node: LineVisual

    def __init__(self, layer: "Line"):
        node = LineVisual()
        super().__init__(layer, node)

        self.layer.events.color.connect(self._on_appearance_change)
        self.layer.events.width.connect(self._on_appearance_change)
        self.layer.events.method.connect(self._on_method_change)

        self.reset()
        self._on_data_change()

    def _on_appearance_change(self, _event=None):
        """Change the appearance of the data"""
        self.node.set_data(color=self.layer.color, width=self.layer.width)

    def _on_data_change(self, _event=None):
        """Set data"""
        self.node.set_data(
            pos=self.layer.data,
            color=self.layer.color,
            width=self.layer.width,
        )

    def _on_method_change(self, _event=None):
        self.node.method = self.layer.method
