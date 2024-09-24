"""Vispy visual for MultiLine Layer type."""

import typing as ty

from napari._vispy.layers.base import VispyBaseLayer

from napari_plot._vispy.visuals.multiline import MultiLineVisual

if ty.TYPE_CHECKING:
    from napari_plot.layers import MultiLine

LINE_MAIN = 0
LINE_HIGHLIGHT = 1
LINE_BOX = 2


class VispyMultiLineLayer(VispyBaseLayer):
    """MultiLine layer."""

    def __init__(self, layer: "MultiLine"):
        node = MultiLineVisual()
        super().__init__(layer, node)

        self.layer.events.color.connect(self._on_appearance_change)
        self.layer.events.width.connect(self._on_width_change)
        self.layer.events.method.connect(self._on_method_change)
        self.layer.events.stream.connect(self._on_pos_change)

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

    def _on_pos_change(self, _event=None):
        """Set data"""
        pos = self.layer._data_view.get_display_data()
        self.node._subvisuals[LINE_MAIN].set_data(pos=pos)
        self.node.update()

    def _on_data_change(self, _event=None):
        """Set data"""
        pos, connect, color = self.layer._data_view.get_display_lines()
        if len(pos) == 0:
            color = (0, 0, 0, 0)
        self.node._subvisuals[LINE_MAIN].set_data(
            pos=pos,
            connect=connect,
            color=color,
            width=self.layer.width,
        )
        self.node.update()

    def _on_method_change(self, _event=None):
        self.node.method = self.layer.method
