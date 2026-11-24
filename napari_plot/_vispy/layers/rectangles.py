"""Sync the Rectangles layer with its VisPy subvisuals."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from napari._vispy.layers.base import VispyBaseLayer

from napari_plot._vispy.visuals.rectangles import RectanglesVisual

if TYPE_CHECKING:
    from napari._vispy.utils.qt_font import FontInfo
    from napari.utils.events import Event

    from napari_plot.layers import Rectangles


class VispyRectanglesLayer(VispyBaseLayer["Rectangles"]):
    """Upload only changed, enabled components of a Rectangles layer."""

    node: RectanglesVisual

    def __init__(self, layer: Rectangles, font_info: FontInfo) -> None:
        super().__init__(layer, RectanglesVisual(font_info), font_info=font_info)
        self._data: np.ndarray | None = None
        self._outline_geometry_dirty = True
        self._outline_color_dirty = True
        self._markers_dirty = True
        self._labels_dirty = True
        layer.events.data.connect(self._on_data_change)
        layer.events.show_rectangles.connect(self._sync_outlines)
        layer.events.outline_color.connect(self._on_outline_color_change)
        layer.events.outline_width.connect(self._on_outline_width_change)
        layer.events.show_markers.connect(self._sync_markers)
        layer.events.marker_size.connect(self._on_markers_change)
        layer.events.marker_color.connect(self._on_markers_change)
        layer.events.marker_symbol.connect(self._on_markers_change)
        layer.events.show_text.connect(self._sync_labels)
        layer.events.text.connect(self._on_labels_change)
        layer.events.text_offset.connect(self._on_labels_change)
        layer.events.text_size.connect(self._on_font_size_change)
        layer.events.text_color.connect(self._on_text_color_change)
        layer.events.adding.connect(self._on_adding_change)
        self.reset()
        self._on_outline_width_change()
        self._on_font_size_change()
        self._on_text_color_change()
        self._on_data_change()

    def _on_data_change(self, _event: Event | None = None) -> None:
        data = self.layer.data
        if self._data is data:
            return
        self._outline_geometry_dirty = True
        if self._data is None or len(self._data) != len(data):
            self._outline_color_dirty = True
        self._data = data
        self._markers_dirty = True
        self._labels_dirty = True
        self._sync_outlines()
        self._sync_markers()
        self._sync_labels()

    def _on_visible_change(self, event: Event | None = None) -> None:
        super()._on_visible_change()
        if self.layer.visible and self._data is not None:
            self._sync_outlines()
            self._sync_markers()
            self._sync_labels()

    def _on_outline_color_change(self, _event: Event | None = None) -> None:
        self._outline_color_dirty = True
        self._sync_outlines()

    def _on_outline_width_change(self, _event: Event | None = None) -> None:
        self.node.outlines.set_width(self.layer.outline_width)
        self.node.preview.set_width(self.layer.outline_width)

    def _on_adding_change(self, _event: Event | None = None) -> None:
        """Show the rectangle being drawn in ADD mode."""
        preview = self.node.preview
        row = self.layer._creating_box
        preview.visible = row is not None
        if row is not None:
            colors = self.layer.outline_color.reshape(-1, 4)
            preview.set_geometry(np.asarray(row, dtype=float).reshape(1, 4))
            preview.set_color(colors[-1] if len(colors) else np.ones(4, dtype=np.float32))
        # subvisuals have no parent, so the canvas must be asked to redraw explicitly
        self.node.update()

    def _sync_outlines(self, _event: Event | None = None) -> None:
        outline = self.node.outlines
        outline.visible = bool(self.layer.show_rectangles and len(self.layer.data))
        if not (outline.visible and self.layer.visible):
            return
        if self._outline_geometry_dirty:
            outline.set_geometry(self.layer.data)
            self._outline_geometry_dirty = False
        if self._outline_color_dirty:
            outline.set_color(self.layer.outline_color)
            self._outline_color_dirty = False

    def _on_markers_change(self, _event: Event | None = None) -> None:
        self._markers_dirty = True
        self._sync_markers()

    def _sync_markers(self, _event: Event | None = None) -> None:
        markers = self.node.markers
        markers.visible = bool(self.layer.show_markers and len(self.layer.data))
        if markers.visible and self.layer.visible and self._markers_dirty:
            markers.set_data(
                pos=self.layer.centers,
                size=self.layer.marker_size,
                symbol=self.layer.marker_symbol,
                edge_width=0,
                face_color=self.layer.marker_color,
            )
            self._markers_dirty = False

    def _on_labels_change(self, _event: Event | None = None) -> None:
        self._labels_dirty = True
        self._sync_labels()

    def _sync_labels(self, _event: Event | None = None) -> None:
        text = self.node.text
        labels = self.layer.text
        if not (self.layer.show_text and labels is not None and len(labels)):
            text.visible = False
            return
        if self.layer.visible and self._labels_dirty:
            labeled = labels != ""
            text.text = labels[labeled].tolist()
            text.pos = self.layer.centers[labeled] + self.layer.text_offset
            self._labels_dirty = False
        text.visible = bool(text.text)

    def _on_text_color_change(self, _event: Event | None = None) -> None:
        self.node.text.color = self.layer.text_color

    def _on_font_size_change(self, _event: Event | None = None) -> None:
        size = self.layer.text_size
        self.node.text.font_size = self._default_font_size if size is None else size
