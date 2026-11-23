"""Qt controls for the Rectangles layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import qtextra.helpers as hp
from napari._qt.utils import qt_signals_blocked, set_widgets_enabled_with_opacity
from napari.layers.points._points_constants import Symbol

from napari_plot._qt.layer_controls.qt_layer_controls_base import QtLayerControls
from napari_plot.layers.rectangles.rectangles import RectangleMode

if TYPE_CHECKING:
    from napari.utils.events import Event

    from napari_plot.layers import Rectangles


class QtRectanglesControls(QtLayerControls):
    """Control rectangle outlines, center markers, and labels."""

    layer: Rectangles
    MODE = RectangleMode

    def __init__(self, layer: Rectangles) -> None:
        super().__init__(layer)
        self.add_button = self._radio_button(
            layer, "draw", RectangleMode.ADD, True, "", tooltip="Drag to add a rectangle"
        )
        self.edit_button = self._radio_button(
            layer, "move", RectangleMode.EDIT, True, "", tooltip="Drag to move a rectangle. Shift-drag to resize."
        )
        self.button_grid.addWidget(self.add_button, 0, 4)
        self.button_grid.addWidget(self.edit_button, 0, 5)
        self._MODE_BUTTONS[layer.mode].setChecked(True)
        self.outlines_checkbox = hp.make_checkbox(self, value=layer.show_rectangles)
        self.markers_checkbox = hp.make_checkbox(self, value=layer.show_markers)
        self.text_checkbox = hp.make_checkbox(self, value=layer.show_text)
        self.width_spinbox = hp.make_double_spin_box(
            self,
            minimum=0.01,
            maximum=max(100, layer.outline_width),
            step_size=0.5,
            n_decimals=2,
            value=layer.outline_width,
            tooltip="Outline width in screen pixels.",
        )
        self.marker_size_spinbox = hp.make_double_spin_box(
            self,
            step_size=1,
            n_decimals=2,
            special_value="Per marker",
            tooltip="Set all marker sizes in screen pixels.",
            func=self._set_marker_size,
        )
        self.marker_symbol_combobox = hp.make_combobox(
            self,
            data={str(symbol): symbol.name.lower().replace("_", " ") for symbol in Symbol},
            tooltip="Set the symbol for all markers.",
            func_index=self._set_marker_symbol,
        )
        self.marker_symbol_combobox.setPlaceholderText("Per marker")
        self.text_size_spinbox = hp.make_double_spin_box(
            self,
            step_size=1,
            n_decimals=2,
            special_value="Application default",
            tooltip="Font size in points.",
            func=self._set_text_size,
        )
        self.outlines_checkbox.toggled.connect(self._set_outlines)
        self.markers_checkbox.toggled.connect(self._set_markers)
        self.text_checkbox.toggled.connect(self._set_text)
        self.width_spinbox.valueChanged.connect(self._set_width)

        layout = self.layout()
        layout.addRow(self.button_grid)
        layout.addRow(self.opacity_label, self.opacity_slider)
        layout.addRow(hp.make_label(self, "blending"), self.blending_combobox)
        layout.addRow(hp.make_label(self, "show outlines"), self.outlines_checkbox)
        layout.addRow(hp.make_label(self, "outline width"), self.width_spinbox)
        layout.addRow(hp.make_label(self, "show markers"), self.markers_checkbox)
        layout.addRow(hp.make_label(self, "marker size"), self.marker_size_spinbox)
        layout.addRow(hp.make_label(self, "marker type"), self.marker_symbol_combobox)
        layout.addRow(hp.make_label(self, "show text"), self.text_checkbox)
        layout.addRow(hp.make_label(self, "font size"), self.text_size_spinbox)

        layer.events.show_rectangles.connect(self._on_style_change)
        layer.events.show_markers.connect(self._on_style_change)
        layer.events.show_text.connect(self._on_style_change)
        layer.events.outline_width.connect(self._on_style_change)
        layer.events.marker_size.connect(self._on_style_change)
        layer.events.marker_symbol.connect(self._on_style_change)
        layer.events.text_size.connect(self._on_style_change)
        layer.events.visible.connect(self._on_visible_change)
        layer.events.mode.connect(self._on_mode_change)
        layer.events.editable.connect(self._on_editable_change)
        self._on_style_change()
        self._on_visible_change()

    def _set_outlines(self, checked: bool) -> None:
        self.layer.show_rectangles = checked

    def _set_markers(self, checked: bool) -> None:
        self.layer.show_markers = checked

    def _set_text(self, checked: bool) -> None:
        self.layer.show_text = checked

    def _set_width(self, value: float) -> None:
        self.layer.outline_width = value

    def _set_marker_size(self, value: float) -> None:
        if value > 0:
            self.layer.marker_size = value
        else:
            self._on_style_change()

    def _set_marker_symbol(self, index: int) -> None:
        if index >= 0:
            self.layer.marker_symbol = self.marker_symbol_combobox.itemData(index)

    def _set_text_size(self, value: float) -> None:
        self.layer.text_size = value or None

    def _on_style_change(self, _event: Event | None = None) -> None:
        for checkbox, checked in (
            (self.outlines_checkbox, self.layer.show_rectangles),
            (self.markers_checkbox, self.layer.show_markers),
            (self.text_checkbox, self.layer.show_text),
        ):
            with qt_signals_blocked(checkbox):
                checkbox.setChecked(checked)
        marker_size = self.layer.marker_size
        for spinbox, value in (
            (self.width_spinbox, self.layer.outline_width),
            (self.marker_size_spinbox, max(0.01, marker_size) if isinstance(marker_size, float) else 0),
            (self.text_size_spinbox, max(0.01, self.layer.text_size) if self.layer.text_size is not None else 0),
        ):
            with qt_signals_blocked(spinbox):
                spinbox.setMaximum(max(100, value))
                spinbox.setValue(value)
        symbol = self.layer.marker_symbol
        with qt_signals_blocked(self.marker_symbol_combobox):
            index = self.marker_symbol_combobox.findData(symbol) if isinstance(symbol, str) else -1
            self.marker_symbol_combobox.setCurrentIndex(index)

    def _on_visible_change(self, _event: Event | None = None) -> None:
        set_widgets_enabled_with_opacity(
            self,
            [
                self.outlines_checkbox,
                self.width_spinbox,
                self.markers_checkbox,
                self.marker_size_spinbox,
                self.marker_symbol_combobox,
                self.text_checkbox,
                self.text_size_spinbox,
            ],
            self.layer.visible,
        )
        self._on_editable_change()

    def _on_editable_change(self) -> None:
        enabled = self.layer.visible and self.layer.editable
        self.add_button.setEnabled(enabled)
        self.edit_button.setEnabled(enabled)
