"""Line layer"""

import typing as ty

import numpy as np
from napari._vispy.layers.base import VispyBaseLayer
from vispy.gloo import Texture2D

from napari_plot._vispy.visuals.line import LineVisual, ScreenDashLine

if ty.TYPE_CHECKING:
    from napari_plot.layers import Line


class VispyLineLayer(VispyBaseLayer):
    """Line layer."""

    layer: "Line"
    node: LineVisual

    def __init__(self, layer: "Line", font_info) -> None:
        node = LineVisual()
        super().__init__(layer, node, font_info=font_info)

        self.layer.events.color.connect(self._on_appearance_change)
        self.layer.events.width.connect(self._on_appearance_change)
        self.layer.events.method.connect(self._on_method_change)
        self.layer.events.dashes.connect(self._on_method_change)

        self.reset()
        self._on_method_change()
        self._on_data_change()

    def _on_appearance_change(self, _event=None):
        """Change the appearance of the data"""
        self.node.set_data(color=self.layer.color, width=self.layer.width)

    def _on_data_change(self, _event=None):
        """Set data"""
        pos = self.layer.data
        # The AGG visual needs at least one segment. A repeated endpoint is invisible and clears old geometry.
        if self.node.method == "agg" and len(pos) < 2:
            pos = np.zeros((2, 2))
        self.node.set_data(
            pos=pos,
            color=self.layer.color,
            width=self.layer.width,
        )
        self._on_visible_change()

    def _on_visible_change(self, _event=None) -> None:
        super()._on_visible_change()
        self.node.visible = self.node.visible and (self.node.method != "agg" or len(self.layer.data) >= 2)

    def _on_method_change(self, _event=None) -> None:
        pattern = self.layer.dashes
        previous = self.node._line_visual
        if pattern is None and isinstance(previous, ScreenDashLine):
            self.node.method = "gl"
        self.node.method = "agg" if pattern is not None else self.layer.method
        if pattern is not None and not isinstance(self.node._line_visual, ScreenDashLine):
            self.node.remove_subvisual(self.node._line_visual)
            self.node._line_visual = ScreenDashLine(self.node)
            self.node.add_subvisual(self.node._line_visual)
        if self.node._line_visual is not previous:
            for visual_filter in tuple(previous._filters):
                previous.detach(visual_filter, previous)
                self.node._line_visual.attach(visual_filter, self.node._line_visual)
        if self.node.method == "agg":
            visual = self.node._line_visual
            key = "solid" if pattern is None else "custom"
            if pattern is not None:
                visual._da = type(visual._da)()
                visual._da[key] = pattern, (1,) * len(pattern)
                # Dash coordinates and signed cap types must survive the texture upload unchanged.
                visual._dash_atlas = Texture2D(visual._da._data, internalformat="rgba32f")
            visual._U["dash_index"], visual._U["dash_period"] = visual._da[key]
        self._on_data_change()
