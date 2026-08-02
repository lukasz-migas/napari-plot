"""VisPy adapter for the Text layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from napari._vispy.layers.base import VispyBaseLayer
from vispy.scene.visuals import Text as TextVisual

if TYPE_CHECKING:
    from napari._vispy.utils.qt_font import FontInfo

    from napari_plot.layers import Text


class VispyTextLayer(VispyBaseLayer):
    """Render labels from a :class:`napari_plot.layers.Text` layer."""

    layer: Text
    node: TextVisual

    def __init__(self, layer: Text, font_info: FontInfo) -> None:
        node = TextVisual(
            face=layer.font_face or font_info.face,
            font_manager=font_info.font_manager,
        )
        super().__init__(layer, node, font_info=font_info)
        self._scale_reference: float | None = None

        for emitter in (
            self.layer.events.text,
            self.layer.events.size,
            self.layer.events.color,
            self.layer.events.alignment,
            self.layer.events.vertical_alignment,
            self.layer.events.rotation,
            self.layer.events.offset,
            self.layer.events.font_face,
            self.layer.events.bold,
            self.layer.events.italic,
        ):
            emitter.connect(self._on_data_change)
        self.layer.events.scaling.connect(self._on_scale_change)
        self.layer.events.scale_factor.connect(self._on_scale_change)

        self.reset()
        self._on_data_change()

    def _on_data_change(self, _event=None) -> None:
        """Update the single native text visual from the layer model."""
        if len(self.layer.data):
            self.node.text = self.layer.text.tolist()
            self.node.pos = self.layer.data + self.layer.offset
            self.node.color = self.layer.color
            self.node.rotation = self.layer.rotation
        else:
            self.node.text = [""]
            self.node.pos = np.zeros((1, 2), dtype=float)
            self.node.color = np.zeros((1, 4), dtype=float)
            self.node.rotation = 0

        self.node.anchors = (
            self.layer.alignment,
            self.layer.vertical_alignment,
        )
        self.node.face = self.layer.font_face or self.font_info.face
        self.node.bold = self.layer.bold
        self.node.italic = self.layer.italic
        self._update_font_size()
        self._on_blending_change()

    def _on_scale_change(self, _event=None) -> None:
        """Update font size relative to the first rendered canvas scale."""
        if self.layer.scaling and self._scale_reference is None:
            self._scale_reference = self.layer.scale_factor
        self._update_font_size()

    def _update_font_size(self) -> None:
        """Apply the configured font size at the current relative zoom."""
        size = self.layer.size
        if self.layer.scaling and self._scale_reference is not None:
            size *= self._scale_reference / self.layer.scale_factor
        self.node.font_size = size
        self.node.update()


__all__ = ["VispyTextLayer"]
