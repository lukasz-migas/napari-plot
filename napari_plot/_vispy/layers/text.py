"""VisPy adapter for the Text layer."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

import numpy as np
from napari._vispy.layers.base import VispyBaseLayer

from napari_plot._vispy.visuals.text import TextVisual

if TYPE_CHECKING:
    from napari._vispy.utils.qt_font import FontInfo

    from napari_plot.layers import Text


class VispyTextLayer(VispyBaseLayer):
    """Render labels from a :class:`napari_plot.layers.Text` layer."""

    layer: Text
    node: TextVisual

    def __init__(self, layer: Text, font_info: FontInfo) -> None:
        node = TextVisual()
        super().__init__(layer, node, font_info=font_info)

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
        """Rebuild native text batches after model data or style changes."""
        grouped_indices: dict[tuple[float, str, str], list[int]] = defaultdict(list)
        for index, key in enumerate(
            zip(
                self.layer.size,
                self.layer.alignment,
                self.layer.vertical_alignment,
                strict=True,
            )
        ):
            grouped_indices[(float(key[0]), str(key[1]), str(key[2]))].append(index)

        positions = self.layer.data + self.layer.offset
        groups = []
        for (size, alignment, vertical_alignment), indices in grouped_indices.items():
            selected = np.asarray(indices, dtype=int)
            groups.append(
                {
                    "text": self.layer.text[selected].tolist(),
                    "pos": positions[selected],
                    "color": self.layer.color[selected],
                    "size": size,
                    "rotation": self.layer.rotation[selected],
                    "alignment": alignment,
                    "vertical_alignment": vertical_alignment,
                }
            )

        self.node.set_groups(
            groups,
            face=self.layer.font_face or self.font_info.face,
            bold=self.layer.bold,
            italic=self.layer.italic,
            font_manager=self.font_info.font_manager,
            scale_factor=self.layer.scale_factor,
            scaling=self.layer.scaling,
        )
        self._on_blending_change()

    def _on_scale_change(self, _event=None) -> None:
        """Update screen-space font sizes when zoom scaling changes."""
        self.node.update_scale(
            scale_factor=self.layer.scale_factor,
            scaling=self.layer.scaling,
        )


__all__ = ["VispyTextLayer"]
