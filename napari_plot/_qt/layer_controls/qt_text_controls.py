"""Qt controls for the Text layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import qtextra.helpers as hp
from napari._qt.utils import qt_signals_blocked, set_widgets_enabled_with_opacity
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont, QGuiApplication
from qtpy.QtWidgets import QFontComboBox

from napari_plot._qt.layer_controls.qt_layer_controls_base import QtLayerControls

if TYPE_CHECKING:
    from napari_plot.layers import Text


class QtTextControls(QtLayerControls):
    """Provide common layer and font controls for text annotations.

    Per-label colors display the first label's value. Changing the color
    control applies the selected value to every label in the layer.
    """

    def __init__(self, layer: Text) -> None:
        super().__init__(layer)
        self.layer.events.size.connect(self._on_size_change)
        self.layer.events.color.connect(self._on_color_change)
        self.layer.events.font_face.connect(self._on_font_face_change)
        self.layer.events.bold.connect(self._on_bold_change)
        self.layer.events.italic.connect(self._on_italic_change)
        self.layer.events.scaling.connect(self._on_scaling_change)
        self.layer.events.alignment.connect(self._on_alignment_change)
        self.layer.events.vertical_alignment.connect(self._on_vertical_alignment_change)
        self.layer.events.visible.connect(self._on_visible_change)

        self.font_face_combobox = QFontComboBox(self)
        self.font_face_combobox.setToolTip("Font family for every label.")
        self.font_face_combobox.setCurrentFont(QFont(self._current_font_face()))
        self.font_face_combobox.currentFontChanged.connect(self.on_change_font_face)

        self.size_slider = hp.make_double_slider_with_text(
            self,
            min_value=1,
            max_value=max(100, self._current_size()),
            step_size=1,
            value=self._current_size(),
            n_decimals=1,
            tooltip="Layer-wide font size in screen points.",
            focus_policy=Qt.FocusPolicy.NoFocus,
        )
        self.size_slider.valueChanged.connect(self.on_change_size)

        self.color_swatch = QColorSwatchEdit(
            initial_color=self._current_color(),
            tooltip="Click to set the color of every label.",
        )
        self.color_swatch.color_changed.connect(self.on_change_color)

        self.bold_checkbox = hp.make_checkbox(
            self,
            value=self.layer.bold,
            tooltip="Render every label in bold.",
        )
        self.bold_checkbox.toggled.connect(self.on_change_bold)

        self.italic_checkbox = hp.make_checkbox(
            self,
            value=self.layer.italic,
            tooltip="Render every label in italics.",
        )
        self.italic_checkbox.toggled.connect(self.on_change_italic)

        self.scaling_checkbox = hp.make_checkbox(
            self,
            value=self.layer.scaling,
            tooltip="Scale font sizes with zoom so labels shrink while zooming out.",
        )
        self.scaling_checkbox.toggled.connect(self.on_change_scaling)

        self.alignment_combobox = hp.make_combobox(
            self,
            tooltip="Layer-wide horizontal text alignment.",
        )
        self.alignment_combobox.addItems(["left", "center", "right"])
        self.alignment_combobox.setCurrentText(self._current_alignment())
        self.alignment_combobox.currentTextChanged.connect(self.on_change_alignment)

        self.vertical_alignment_combobox = hp.make_combobox(
            self,
            tooltip="Layer-wide vertical text alignment.",
        )
        self.vertical_alignment_combobox.addItems(["top", "center", "baseline", "bottom"])
        self.vertical_alignment_combobox.setCurrentText(self._current_vertical_alignment())
        self.vertical_alignment_combobox.currentTextChanged.connect(self.on_change_vertical_alignment)

        self.layout().addRow(self.button_grid)
        self.layout().addRow(self.opacity_label, self.opacity_slider)
        self.layout().addRow(hp.make_label(self, "blending"), self.blending_combobox)
        self.layout().addRow(hp.make_label(self, "font"), self.font_face_combobox)
        self.layout().addRow(hp.make_label(self, "font size"), self.size_slider)
        self.layout().addRow(hp.make_label(self, "font color"), self.color_swatch)
        self.layout().addRow(hp.make_label(self, "bold"), self.bold_checkbox)
        self.layout().addRow(hp.make_label(self, "italic"), self.italic_checkbox)
        self.layout().addRow(hp.make_label(self, "scale with zoom"), self.scaling_checkbox)
        self.layout().addRow(hp.make_label(self, "alignment"), self.alignment_combobox)
        self.layout().addRow(
            hp.make_label(self, "vertical alignment"),
            self.vertical_alignment_combobox,
        )
        self._on_visible_change()

    def _current_size(self) -> float:
        """Return the layer-wide font size."""
        return self.layer.size

    def _current_color(self) -> np.ndarray:
        """Return the first label color or the empty-layer default."""
        return self.layer.color[0] if len(self.layer.color) else self.layer._default_color

    def _current_alignment(self) -> str:
        """Return the layer-wide horizontal alignment."""
        return self.layer.alignment

    def _current_vertical_alignment(self) -> str:
        """Return the layer-wide vertical alignment."""
        return self.layer.vertical_alignment

    def _current_font_face(self) -> str:
        """Return the configured font family or the application default."""
        return self.layer.font_face or QGuiApplication.font().family()

    def on_change_size(self, value: float) -> None:
        """Apply a font size to every label."""
        self.layer.size = value

    def _on_size_change(self, _event=None) -> None:
        """Update the size control after a model change."""
        value = self._current_size()
        if value > self.size_slider.maximum():
            self.size_slider.setMaximum(value)
        with qt_signals_blocked(self.size_slider):
            self.size_slider.setValue(value)

    def on_change_color(self, color: np.ndarray) -> None:
        """Apply a color to every label."""
        self.layer.color = color

    def _on_color_change(self, _event=None) -> None:
        """Update the color swatch after a model change."""
        with qt_signals_blocked(self.color_swatch):
            self.color_swatch.setColor(self._current_color())

    def on_change_font_face(self, font: QFont) -> None:
        """Apply a font family to every label."""
        self.layer.font_face = font.family()

    def _on_font_face_change(self, _event=None) -> None:
        """Update the font family control after a model change."""
        with qt_signals_blocked(self.font_face_combobox):
            self.font_face_combobox.setCurrentFont(QFont(self._current_font_face()))

    def on_change_bold(self, checked: bool) -> None:
        """Set the layer-wide bold style."""
        self.layer.bold = checked

    def _on_bold_change(self, _event=None) -> None:
        """Update the bold control after a model change."""
        with qt_signals_blocked(self.bold_checkbox):
            self.bold_checkbox.setChecked(self.layer.bold)

    def on_change_italic(self, checked: bool) -> None:
        """Set the layer-wide italic style."""
        self.layer.italic = checked

    def _on_italic_change(self, _event=None) -> None:
        """Update the italic control after a model change."""
        with qt_signals_blocked(self.italic_checkbox):
            self.italic_checkbox.setChecked(self.layer.italic)

    def on_change_scaling(self, checked: bool) -> None:
        """Set whether font sizes scale with zoom."""
        self.layer.scaling = checked

    def _on_scaling_change(self, _event=None) -> None:
        """Update the zoom-scaling control after a model change."""
        with qt_signals_blocked(self.scaling_checkbox):
            self.scaling_checkbox.setChecked(self.layer.scaling)

    def on_change_alignment(self, value: str) -> None:
        """Apply a horizontal alignment to every label."""
        self.layer.alignment = value

    def _on_alignment_change(self, _event=None) -> None:
        """Update horizontal alignment after a model change."""
        with qt_signals_blocked(self.alignment_combobox):
            self.alignment_combobox.setCurrentText(self._current_alignment())

    def on_change_vertical_alignment(self, value: str) -> None:
        """Apply a vertical alignment to every label."""
        self.layer.vertical_alignment = value

    def _on_vertical_alignment_change(self, _event=None) -> None:
        """Update vertical alignment after a model change."""
        with qt_signals_blocked(self.vertical_alignment_combobox):
            self.vertical_alignment_combobox.setCurrentText(self._current_vertical_alignment())

    def _on_visible_change(self, _event=None) -> None:
        """Enable common controls only while the layer is visible."""
        set_widgets_enabled_with_opacity(
            self,
            [
                self.opacity_slider,
                self.blending_combobox,
                self.font_face_combobox,
                self.size_slider,
                self.color_swatch,
                self.bold_checkbox,
                self.italic_checkbox,
                self.scaling_checkbox,
                self.alignment_combobox,
                self.vertical_alignment_combobox,
            ],
            self.layer.visible,
        )


__all__ = ["QtTextControls"]
