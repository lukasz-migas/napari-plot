"""VisPy adapter for the Areas layer."""

from __future__ import annotations

import typing as ty

from napari._vispy.layers.base import VispyBaseLayer

from napari_plot._vispy.visuals.bar import BarVisual

if ty.TYPE_CHECKING:
    from napari_plot.layers import Areas


class VispyAreasLayer(VispyBaseLayer):
    """Render area fills and outlines with the same mesh + segments visual as bars."""

    layer: Areas
    node: BarVisual

    def __init__(self, layer: Areas, font_info) -> None:
        super().__init__(layer, BarVisual(), font_info=font_info)
        for event_name in ("orientation", "fill_color", "border_color", "border_width", "stream"):
            getattr(layer.events, event_name).connect(self._on_data_change)
        self.reset()
        self._on_data_change()

    def _on_data_change(self, _event=None) -> None:
        """Rebuild fill and outline geometry."""
        vertices, faces, face_colors = self.layer._mesh_data()
        has_fill = bool(len(faces))
        has_border = has_fill and self.layer.border_width > 0
        self.node.mesh.visible = has_fill
        self.node.border.visible = has_border
        if has_fill:
            self.node.mesh.set_data(vertices=vertices, faces=faces, face_colors=face_colors)
        if has_border:
            border_vertices, border_colors = self.layer._border_data()
            self.node.border.set_data(
                pos=border_vertices, connect="segments", color=border_colors, width=self.layer.border_width
            )
        self.node.update()


__all__ = ["VispyAreasLayer"]
