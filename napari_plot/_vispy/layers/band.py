"""VisPy adapter for a filled band."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from napari._vispy.layers.base import VispyBaseLayer
from vispy.scene.visuals import Mesh

if TYPE_CHECKING:
    from napari._vispy.utils.qt_font import FontInfo

    from napari_plot.layers.band import Band


class VispyBandLayer(VispyBaseLayer):
    """Draw all connected band intervals in one mesh."""

    layer: Band
    node: Mesh

    def __init__(self, layer: Band, font_info: FontInfo) -> None:
        self._has_triangles = False
        super().__init__(layer, Mesh(), font_info=font_info)
        layer.events.fill_color.connect(self._on_fill_color_change)
        self.reset()
        self._on_data_change()

    def _on_data_change(self) -> None:
        triangles = self.layer._triangles()
        self._has_triangles = bool(len(triangles))
        if self._has_triangles:
            vertices = triangles.reshape(-1, 2)
            faces = np.arange(len(vertices), dtype=np.uint32).reshape(-1, 3)
            self.node.set_data(vertices=vertices, faces=faces, color=self.layer.fill_color)
        self._on_visible_change()
        self.node.update()

    def _on_visible_change(self) -> None:
        self.node.visible = self.layer.visible and self._has_triangles

    def _on_fill_color_change(self) -> None:
        self.node.color = self.layer.fill_color
