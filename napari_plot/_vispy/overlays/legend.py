"""VisPy renderer for the canvas legend overlay."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

import numpy as np
from napari._vispy.overlays.base import ViewerOverlayMixin, VispyCanvasOverlay
from napari._vispy.utils.qt_font import FontInfo
from napari.utils.colormaps import ensure_colormap
from napari.utils.events import disconnect_events
from vispy.scene.visuals import Compound, Line, Markers, Rectangle, Text

from napari_plot.components.legend import LegendEntry, LegendOverlay

FALLBACK_MARKER = "square"
TEXT_WIDTH_FACTOR = 1.05
TEXT_EXTRA_PADDING_FACTOR = 1.5
MARKER_TEXT_GAP = 8.0


def legend_entry_color(entry: LegendEntry, fallback: ty.Any) -> np.ndarray:
    """Return the explicit, mapped, or fallback color for an entry."""
    if entry.color is not None:
        return np.asarray(entry.color, dtype=float)
    if entry.colormap is not None:
        try:
            return np.asarray(ensure_colormap(entry.colormap).map(np.asarray([0.5]))[0], dtype=float)
        except (AttributeError, KeyError, TypeError, ValueError):
            pass
    return np.asarray(fallback, dtype=float)


def _has_marker_column(entries: ty.Sequence[LegendEntry]) -> bool:
    return any(entry.marker is not None or entry.color is not None or entry.colormap is not None for entry in entries)


def legend_layout_size(overlay: LegendOverlay) -> tuple[float, float]:
    """Estimate legend canvas size from its labels and style."""
    if not overlay.entries:
        return 0.0, 0.0
    labels = [entry.label for entry in overlay.entries]
    row_height = max(overlay.font_size, overlay.marker_size) + overlay.row_spacing
    marker_width = overlay.marker_size + MARKER_TEXT_GAP if _has_marker_column(overlay.entries) else 0.0
    text_width = max(len(label) for label in labels) * overlay.font_size * TEXT_WIDTH_FACTOR
    extra_padding = overlay.font_size * TEXT_EXTRA_PADDING_FACTOR
    x_size = (2 * overlay.padding) + marker_width + text_width + extra_padding
    y_size = (2 * overlay.padding) + (len(labels) * row_height) - overlay.row_spacing
    return float(x_size), float(y_size)


def _border_segments(x_size: float, y_size: float) -> np.ndarray:
    corners = np.asarray(
        [[0.0, 0.0, 0.0], [x_size, 0.0, 0.0], [x_size, y_size, 0.0], [0.0, y_size, 0.0]],
        dtype=float,
    )
    return np.asarray(
        [corners[0], corners[1], corners[1], corners[2], corners[2], corners[3], corners[3], corners[0]],
        dtype=float,
    )


class VispyLegendOverlay(ViewerOverlayMixin, VispyCanvasOverlay):
    """Canvas-space legend composed of background, border, text, and markers."""

    def __init__(
        self,
        *,
        viewer,
        overlay: LegendOverlay,
        font_info: FontInfo,
        parent=None,
    ) -> None:
        self._background = Rectangle(center=(0, 0), width=1, height=1, color=(0, 0, 0, 0))
        self._border = Line(connect="segments", method="gl")
        self._text = Text(text="", pos=(0, 0, 0), anchor_x="left", anchor_y="center")
        self._markers: list[Markers] = []
        self._connected_entries: tuple[LegendEntry, ...] = ()
        self._mouse_emitter = None
        node = Compound([self._background, self._border, self._text], parent=parent)
        super().__init__(node=node, viewer=viewer, overlay=overlay, font_info=font_info, parent=parent)

        overlay.events.entries.connect(self._on_entries_change)
        for event_name in (
            "text_color",
            "font_size",
            "marker_size",
            "row_spacing",
            "padding",
            "background_color",
            "border_color",
            "border_width",
        ):
            getattr(overlay.events, event_name).connect(self._on_data_change)
        self._connect_entry_events()
        self._connect_mouse_events()
        self.reset()

    def _connect_mouse_events(self) -> None:
        canvas = self.node.canvas
        emitter = None if canvas is None else canvas.events.mouse_press
        if emitter is self._mouse_emitter:
            return
        if self._mouse_emitter is not None:
            with suppress(ValueError):
                self._mouse_emitter.disconnect(self._on_mouse_press)
        self._mouse_emitter = emitter
        if emitter is not None:
            emitter.connect(self._on_mouse_press)

    def _connect_entry_events(self) -> None:
        self._disconnect_entry_events()
        for entry in self.overlay.entries:
            entry.events.label.connect(self._on_data_change)
            entry.events.marker.connect(self._on_data_change)
            entry.events.color.connect(self._on_data_change)
            entry.events.colormap.connect(self._on_data_change)
        self._connected_entries = tuple(self.overlay.entries)

    def _disconnect_entry_events(self) -> None:
        for entry in self._connected_entries:
            disconnect_events(entry.events, self)
        self._connected_entries = ()

    def _on_entries_change(self, _event=None) -> None:
        """Reconnect row events and redraw the legend."""
        self._connect_entry_events()
        self._on_data_change()

    def _ensure_marker_count(self, count: int) -> None:
        while len(self._markers) > count:
            self.node.remove_subvisual(self._markers.pop())
        while len(self._markers) < count:
            marker = Markers(scaling="fixed")
            self.node.add_subvisual(marker)
            self._markers.append(marker)

    def _clear_visuals(self) -> None:
        self.x_size = 0.0
        self.y_size = 0.0
        self._background.visible = False
        self._border.set_data(pos=np.empty((0, 3)), color=(0, 0, 0, 0), width=0)
        self._text.text = ""
        self._text.visible = False
        self._ensure_marker_count(0)

    def _row_positions(self) -> np.ndarray:
        row_height = max(self.overlay.font_size, self.overlay.marker_size) + self.overlay.row_spacing
        row_center = max(self.overlay.font_size, self.overlay.marker_size) / 2
        text_x = self.overlay.padding
        if _has_marker_column(self.overlay.entries):
            text_x += self.overlay.marker_size + MARKER_TEXT_GAP
        return np.asarray(
            [
                [text_x, self.overlay.padding + row_center + (index * row_height), 0.0]
                for index, _entry in enumerate(self.overlay.entries)
            ],
            dtype=float,
        )

    def _on_data_change(self, _event=None) -> None:
        """Redraw the legend from the overlay model."""
        if not self.overlay.entries:
            self._clear_visuals()
            self._on_position_change()
            self.node.update()
            return

        self.x_size, self.y_size = legend_layout_size(self.overlay)
        text_positions = self._row_positions()
        self._background.center = self.x_size / 2, self.y_size / 2
        self._background.width = self.x_size
        self._background.height = self.y_size
        self._background.color = self.overlay.background_color
        self._background.visible = True
        self._background.update()

        if self.overlay.border_width > 0:
            self._border.set_data(
                pos=_border_segments(self.x_size, self.y_size),
                color=self.overlay.border_color,
                width=self.overlay.border_width,
            )
        else:
            self._border.set_data(pos=np.empty((0, 3)), color=(0, 0, 0, 0), width=0)

        self._text.text = [entry.label for entry in self.overlay.entries]
        self._text.pos = text_positions
        self._text.color = self.overlay.text_color
        self._text.font_size = self.overlay.font_size
        self._text.visible = True

        marker_entries = [
            (entry, position)
            for entry, position in zip(self.overlay.entries, text_positions, strict=True)
            if entry.marker is not None or entry.color is not None or entry.colormap is not None
        ]
        self._ensure_marker_count(len(marker_entries))
        marker_x = self.overlay.padding + (self.overlay.marker_size / 2)
        for marker, (entry, position) in zip(self._markers, marker_entries, strict=True):
            color = legend_entry_color(entry, self.overlay.text_color)
            marker_pos = np.asarray([[marker_x, position[1], 0.0]], dtype=float)
            try:
                marker.set_data(
                    pos=marker_pos,
                    symbol=entry.marker or FALLBACK_MARKER,
                    size=self.overlay.marker_size,
                    face_color=color,
                    edge_color=color,
                    edge_width=0,
                )
            except ValueError:
                marker.set_data(
                    pos=marker_pos,
                    symbol=FALLBACK_MARKER,
                    size=self.overlay.marker_size,
                    face_color=color,
                    edge_color=color,
                    edge_width=0,
                )

        self._on_position_change()
        self._on_blending_change()
        self.node.update()

    def _on_position_change(self, _event=None) -> None:
        """Position the legend in its selected canvas corner or center."""
        self._connect_mouse_events()
        if self.node.canvas is not None and self.node.parent is not None:
            parent_size = np.asarray(getattr(self.node.parent, "size", self.node.canvas.size), dtype=float)
            width, height = parent_size[:2]
            padding = 10.0
            position = self.overlay.position.value
            if "left" in position:
                x = padding
            elif "right" in position:
                x = width - self.x_size - padding
            else:
                x = (width - self.x_size) / 2
            y = padding if "top" in position else height - self.y_size - padding
            self.node.transform.translate = [max(0.0, x), max(0.0, y), 0.0, 0.0]
        else:
            super()._on_position_change()
        self.node.update()
        with suppress(AttributeError):
            self.node.canvas.update()

    def _on_mouse_press(self, event) -> None:
        """Toggle the layer represented by a clicked legend row."""
        if not self.overlay.visible or getattr(event, "button", None) != 1 or self.node.parent is None:
            return
        parent_pos = np.asarray(getattr(self.node.parent, "pos", (0.0, 0.0)), dtype=float)
        translation = np.asarray(self.node.transform.translate[:2], dtype=float)
        local = np.asarray(event.pos[:2], dtype=float) - parent_pos[:2] - translation
        if not (0 <= local[0] <= self.x_size and 0 <= local[1] <= self.y_size):
            return
        row_height = max(self.overlay.font_size, self.overlay.marker_size) + self.overlay.row_spacing
        row = int((local[1] - self.overlay.padding) // row_height)
        if row < 0 or row >= len(self.overlay.entries):
            return
        layer_name = self.overlay.entries[row].layer_name
        if layer_name is None:
            return
        with suppress(KeyError):
            layer = self.viewer.layers[layer_name]
            layer.visible = not layer.visible
            event.handled = True

    def reset(self) -> None:
        super().reset()
        self._on_data_change()

    def close(self) -> None:
        self._disconnect_entry_events()
        if self._mouse_emitter is not None:
            with suppress(ValueError):
                self._mouse_emitter.disconnect(self._on_mouse_press)
            self._mouse_emitter = None
        self._ensure_marker_count(0)
        super().close()


__all__ = ["VispyLegendOverlay", "legend_entry_color", "legend_layout_size"]
