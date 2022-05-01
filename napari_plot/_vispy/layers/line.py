"""Line layer"""
import typing as ty

from napari._vispy.layers.base import VispyBaseLayer

from ..visuals.line import LineVisual

if ty.TYPE_CHECKING:
    from ...layers import Line


LINE_MAIN = 0
LINE_SCATTER = 1


class VispyLineLayer(VispyBaseLayer):
    """Line layer."""

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
        self.node._subvisuals[LINE_MAIN].set_data(color=self.layer.color, width=self.layer.width)

    def _on_data_change(self, _event=None):
        """Set data"""
        self.node._subvisuals[LINE_MAIN].set_data(
            pos=self.layer.data,
            color=self.layer.color,
            width=self.layer.width,
        )

    def _on_method_change(self, _event=None):
        self.node._subvisuals[LINE_MAIN].method = self.layer.method
