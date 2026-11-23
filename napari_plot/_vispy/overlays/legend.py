"""VisPy renderer for the canvas legend overlay."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

import numpy as np
from napari._vispy.overlays.base import ViewerOverlayMixin, VispyCanvasOverlay
from napari._vispy.utils.qt_font import FontInfo
from napari.utils.colormaps import ensure_colormap
from napari.utils.events import disconnect_events
from vispy.scene import Widget
from vispy.scene.visuals import Compound, Line, Markers, Rectangle, Text
from vispy.scene.widgets import Grid

from napari_plot._vispy.plot_cell import detach_widget
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


def _has_marker(entry: LegendEntry) -> bool:
    return entry.marker is not None or entry.color is not None or entry.colormap is not None


def _legend_layout(
    overlay: LegendOverlay, entries: ty.Sequence[LegendEntry]
) -> tuple[tuple[float, float], np.ndarray, np.ndarray]:
    font_size = overlay.effective_font_size
    content_height = max(font_size, overlay.marker_size)
    row_height = content_height + overlay.row_spacing
    columns = min(overlay.ncols, max(len(entries), 1))
    rows = (len(entries) + columns - 1) // columns
    title_height = row_height if overlay.title else 0.0
    positions = np.zeros((len(entries), 3))
    edges = [float(overlay.padding)]
    for col in range(columns):
        column_entries = entries[col::columns]
        if not column_entries:
            break
        marker_width = overlay.marker_size + MARKER_TEXT_GAP if any(map(_has_marker, column_entries)) else 0.0
        text_width = max(len(entry.label) for entry in column_entries) * font_size * TEXT_WIDTH_FACTOR
        positions[col::columns, 0] = edges[-1] + marker_width
        positions[col::columns, 1] = (
            overlay.padding + title_height + content_height / 2 + np.arange(rows)[: len(column_entries)] * row_height
        )
        edges.append(edges[-1] + marker_width + text_width + font_size * TEXT_EXTRA_PADDING_FACTOR)
    title_width = len(overlay.title) * font_size * TEXT_WIDTH_FACTOR + font_size * TEXT_EXTRA_PADDING_FACTOR
    width = max(edges[-1] - overlay.padding, title_width if overlay.title else 0.0)
    height = (rows * row_height) + title_height - overlay.row_spacing
    size = (width + 2 * overlay.padding, height + 2 * overlay.padding) if entries or overlay.title else (0.0, 0.0)
    return size, positions, np.asarray(edges)


def legend_layout_size(overlay: LegendOverlay, entries: ty.Sequence[LegendEntry] | None = None) -> tuple[float, float]:
    """Estimate the legend size for the given entries, including its title."""
    return _legend_layout(overlay, overlay.entries if entries is None else entries)[0]


_STYLE_EVENTS = (
    "text_color",
    "font_size",
    "marker_size",
    "row_spacing",
    "padding",
    "background_color",
    "border_color",
    "border_width",
    "title",
    "ncols",
)


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
        layer_filter: tuple[frozenset[str], bool] | None = None,
    ) -> None:
        self._layer_filter = layer_filter
        self._background = Rectangle(center=(0, 0), width=1, height=1, color=(0, 0, 0, 0))
        self._border = Line(connect="segments", method="gl")
        self._text = Text(text="", pos=(0, 0, 0), anchor_x="left", anchor_y="center")
        self._markers: list[Markers] = []
        self._column_edges = np.empty(0)
        self._outside_widget = Widget()
        self._connected_entries: tuple[LegendEntry, ...] = ()
        self._mouse_emitter = None
        node = Compound([self._background, self._border, self._text], parent=parent)
        super().__init__(node=node, viewer=viewer, overlay=overlay, font_info=font_info, parent=parent)

        # shows only rows whose layer passes the filter (one cell's layers in grid mode); `None` shows all rows
        overlay.events.entries.connect(self._on_entries_change)
        for event_name in _STYLE_EVENTS:
            getattr(overlay.events, event_name).connect(self._on_data_change)
        viewer.events.theme.connect(self._on_data_change)
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
            entry.events.layer_name.connect(self._on_data_change)
        self._connected_entries = tuple(self.overlay.entries)

    def _disconnect_entry_events(self) -> None:
        for entry in self._connected_entries:
            disconnect_events(entry.events, self)
        self._connected_entries = ()

    @property
    def _entries(self) -> tuple[LegendEntry, ...]:
        """Rows shown by this visual: rows without a layer, and rows whose layer passes the layer filter."""
        entries = tuple(self.overlay.entries)
        if self._layer_filter is None:
            return entries
        names, include = self._layer_filter
        return tuple(entry for entry in entries if entry.layer_name is None or (entry.layer_name in names) == include)

    def set_layer_filter(self, layer_filter: tuple[frozenset[str], bool] | None) -> None:
        """Show rows for the given layer membership, preserving manual rows."""
        if self._layer_filter == layer_filter:
            return
        self._layer_filter = layer_filter
        self._on_data_change()

    def _on_font_size_change(self) -> None:
        self._on_data_change()

    def _on_entries_change(self, _event=None) -> None:
        """Reconnect row events and redraw the legend."""
        self._connect_entry_events()
        self._on_data_change()

    def _ensure_marker_count(self, count: int) -> None:
        # vispy's Compound only attaches parent clippers to subvisuals present at attach time,
        # but detaches them from all current subvisuals, so keep late-added markers in sync.
        clippers = list(getattr(self.node, "_clippers", {}).values())
        while len(self._markers) > count:
            marker = self._markers.pop()
            for clipper in clippers:
                with suppress(ValueError):
                    marker.detach(clipper, marker)
            self.node.remove_subvisual(marker)
        while len(self._markers) < count:
            marker = Markers(scaling="fixed")
            self.node.add_subvisual(marker)
            for clipper in clippers:
                marker.attach(clipper, marker)
            self._markers.append(marker)

    def _clear_visuals(self) -> None:
        self.x_size = 0.0
        self.y_size = 0.0
        self._background.visible = False
        self._border.set_data(pos=np.empty((0, 3)), color=(0, 0, 0, 0), width=0)
        self._text.text = ""
        self._text.visible = False
        self._ensure_marker_count(0)

    def _on_data_change(self, _event=None) -> None:
        """Redraw the legend from the overlay model."""
        entries = self._entries
        if not entries and not self.overlay.title:
            self._clear_visuals()
            self._on_position_change()
            self.node.update()
            return

        (self.x_size, self.y_size), text_positions, self._column_edges = _legend_layout(self.overlay, entries)
        text_color, background_color, border_color = self.overlay.colors_for_theme(self.viewer.theme)
        self._background.center = self.x_size / 2, self.y_size / 2
        self._background.width = self.x_size
        self._background.height = self.y_size
        self._background.color = background_color
        self._background.visible = True
        self._background.update()

        if self.overlay.border_width > 0:
            self._border.set_data(
                pos=_border_segments(self.x_size, self.y_size),
                color=border_color,
                width=self.overlay.border_width,
            )
        else:
            self._border.set_data(pos=np.empty((0, 3)), color=(0, 0, 0, 0), width=0)

        labels = [entry.label for entry in entries]
        positions = text_positions
        if self.overlay.title:
            height = max(self.overlay.effective_font_size, self.overlay.marker_size)
            labels.insert(0, self.overlay.title)
            positions = np.vstack(([self.overlay.padding, self.overlay.padding + height / 2, 0], positions))
        self._text.text = labels
        self._text.pos = positions
        self._text.color = text_color
        self._text.font_size = self.overlay.effective_font_size
        self._text.visible = True

        marker_entries = [
            (entry, position, self._column_edges[index % (len(self._column_edges) - 1)])
            for index, (entry, position) in enumerate(zip(entries, text_positions, strict=True))
            if _has_marker(entry)
        ]
        self._ensure_marker_count(len(marker_entries))
        for marker, (entry, position, column_x) in zip(self._markers, marker_entries, strict=True):
            color = legend_entry_color(entry, text_color)
            marker_x = column_x + self.overlay.marker_size / 2
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
        """Report the legend size; the canvas places the legend when tiling."""
        self._connect_mouse_events()
        super()._on_position_change()
        self.node.update()
        with suppress(AttributeError):
            self.node.canvas.update()

    def _on_mouse_press(self, event) -> None:
        """Toggle the layer represented by a clicked legend row."""
        if not self.overlay.visible or getattr(event, "button", None) != 1 or self.node.parent is None:
            return
        # the legend's view box can be nested in a plot cell (grid mode), so map through the whole node tree
        root = self.node.parent
        while root.parent is not None:
            root = root.parent
        origin = np.asarray(self.node.node_transform(root).map([0, 0])[:2], dtype=float)
        local = np.asarray(event.pos[:2], dtype=float) - origin
        if not (0 <= local[0] <= self.x_size and 0 <= local[1] <= self.y_size):
            return
        row_height = max(self.overlay.effective_font_size, self.overlay.marker_size) + self.overlay.row_spacing
        title_height = row_height if self.overlay.title else 0.0
        row = int((local[1] - self.overlay.padding - title_height) // row_height)
        columns = len(self._column_edges) - 1
        entries = self._entries
        if not entries or row < 0:
            return
        column = int(np.clip(np.searchsorted(self._column_edges, local[0], side="right") - 1, 0, columns - 1))
        index = row * columns + column
        if index >= len(entries):
            return
        layer_name = entries[index].layer_name
        if layer_name is None:
            return
        with suppress(KeyError):
            layer = self.viewer.layers[layer_name]
            layer.visible = not layer.visible
            event.handled = True

    def place(self, view: Widget, grid: Grid, row: int) -> None:
        """Move the legend between the plot and a dedicated column to its right."""
        widget = self._outside_widget
        outside = self.overlay.outside and self.overlay.visible and self.x_size > 0
        if isinstance(widget.parent, Grid) and (not outside or widget.parent is not grid):
            self.node.parent = view
            detach_widget(widget.parent, widget)
        if not outside:
            return
        width = self.x_size + 12
        if widget.parent is not grid:
            widget.width_max = width
            grid.add_widget(widget, row=row, col=3)
            self.node.parent = widget
        elif widget.width_max != width:
            widget.width_max = width
            grid._need_solver_recreate = True
        height = float(view.size[1])
        vertical = str(self.overlay.position).split("_")[0]
        extra_height = max(0.0, height - self.y_size - 12)
        offset = {"top": 0.0, "middle": extra_height / 2, "bottom": extra_height}[vertical]
        self.node.transform.translate = [6, 6 + offset, 0, 0]
        self._on_box_change()

    def close(self) -> None:
        # the overlay model outlives this visual (e.g. a legend copy in a plot cell that was removed)
        self.overlay.events.entries.disconnect(self._on_entries_change)
        for event_name in _STYLE_EVENTS:
            getattr(self.overlay.events, event_name).disconnect(self._on_data_change)
        self._disconnect_entry_events()
        if self._mouse_emitter is not None:
            with suppress(ValueError):
                self._mouse_emitter.disconnect(self._on_mouse_press)
            self._mouse_emitter = None
        self._ensure_marker_count(0)
        if isinstance(self._outside_widget.parent, Grid):
            detach_widget(self._outside_widget.parent, self._outside_widget)
        super().close()


__all__ = ["VispyLegendOverlay", "legend_entry_color", "legend_layout_size"]
