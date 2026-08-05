"""VisPy adapter for the Bar layer."""

from __future__ import annotations

import typing as ty

from napari._vispy.layers.base import VispyBaseLayer

from napari_plot._vispy.visuals.bar import BarVisual

if ty.TYPE_CHECKING:
    from napari_plot.layers import Bar


class VispyBarLayer(VispyBaseLayer):
    """Render finite bar fills, borders, and selection highlights."""

    layer: Bar
    node: BarVisual

    def __init__(self, layer: Bar, font_info) -> None:
        node = BarVisual()
        super().__init__(layer, node, font_info=font_info)
        for event_name in (
            "orientation",
            "baseline",
            "width",
            "fill_color",
            "border_color",
            "border_width",
            "highlight",
        ):
            getattr(layer.events, event_name).connect(self._on_data_change)
        self.reset()
        self._on_data_change()

    def _on_data_change(self, _event=None) -> None:
        """Rebuild bar fill and border geometry."""
        vertices, faces, vertex_colors = self.layer._mesh_data()
        border_vertices, border_colors = self.layer._border_data()
        self.node.mesh.set_data(vertices=vertices, faces=faces, vertex_colors=vertex_colors)
        self.node.border.set_data(
            pos=border_vertices,
            connect="segments",
            color=border_colors,
            width=self.layer.border_width,
        )
        self.node.update()


__all__ = ["VispyBarLayer"]
