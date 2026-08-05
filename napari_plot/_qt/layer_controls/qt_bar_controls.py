"""Qt controls for the Bar layer."""

from __future__ import annotations

import typing as ty

import qtextra.helpers as hp
from napari._qt.utils import qt_signals_blocked, set_widgets_enabled_with_opacity
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit

from napari_plot._qt.layer_controls.qt_layer_controls_base import QtLayerControls

if ty.TYPE_CHECKING:
    from napari_plot.layers import Bar


class QtBarControls(QtLayerControls):
    """Controls for bar orientation, geometry, and appearance."""

    def __init__(self, layer: Bar) -> None:
        super().__init__(layer)
        for event_name in (
            "orientation",
            "baseline",
            "width",
            "fill_color",
            "border_color",
            "border_width",
        ):
            getattr(layer.events, event_name).connect(self._on_layer_change)
        layer.events.visible.connect(self._on_visible_change)

        self.orientation_combobox = hp.make_combobox(
            self,
            items=["vertical", "horizontal"],
            value=layer.orientation.value,
            tooltip="Direction in which bars extend from the baseline.",
        )
        self.orientation_combobox.currentTextChanged.connect(self.on_change_orientation)
        self.baseline_spinbox = hp.make_double_spin_box(
            self,
            minimum=-1e12,
            maximum=1e12,
            n_decimals=4,
            value=layer.baseline,
            func=self.on_change_baseline,
        )
        self.width_spinbox = hp.make_double_spin_box(
            self,
            minimum=0.001,
            maximum=1e12,
            n_decimals=4,
            value=layer.width,
            func=self.on_change_width,
        )
        self.border_width_spinbox = hp.make_double_spin_box(
            self,
            minimum=0,
            maximum=100,
            n_decimals=2,
            value=layer.border_width,
            func=self.on_change_border_width,
        )
        self.fill_color_swatch = QColorSwatchEdit(
            initial_color=layer.fill_color[0] if len(layer.fill_color) else "white",
            tooltip="Set one fill color for every bar.",
        )
        self.fill_color_swatch.color_changed.connect(self.on_change_fill_color)
        self.border_color_swatch = QColorSwatchEdit(
            initial_color=layer.border_color[0] if len(layer.border_color) else "dimgray",
            tooltip="Set one border color for every bar.",
        )
        self.border_color_swatch.color_changed.connect(self.on_change_border_color)

        self.layout().addRow(self.button_grid)
        self.layout().addRow(self.opacity_label, self.opacity_slider)
        self.layout().addRow(hp.make_label(self, "blending"), self.blending_combobox)
        self.layout().addRow(hp.make_label(self, "orientation"), self.orientation_combobox)
        self.layout().addRow(hp.make_label(self, "baseline"), self.baseline_spinbox)
        self.layout().addRow(hp.make_label(self, "bar width"), self.width_spinbox)
        self.layout().addRow(hp.make_label(self, "fill color"), self.fill_color_swatch)
        self.layout().addRow(hp.make_label(self, "border color"), self.border_color_swatch)
        self.layout().addRow(hp.make_label(self, "border width"), self.border_width_spinbox)
        self._on_visible_change()

    def on_change_orientation(self, value: str) -> None:
        """Set bar orientation from the selector."""
        self.layer.orientation = value

    def on_change_baseline(self, value: float) -> None:
        """Set the shared bar baseline."""
        self.layer.baseline = value

    def on_change_width(self, value: float) -> None:
        """Set bar width in data coordinates."""
        self.layer.width = value

    def on_change_border_width(self, value: float) -> None:
        """Set border width in screen pixels."""
        self.layer.border_width = value

    def on_change_fill_color(self, color) -> None:
        """Apply one fill color to all bars."""
        self.layer.fill_color = color

    def on_change_border_color(self, color) -> None:
        """Apply one border color to all bars."""
        self.layer.border_color = color

    def _on_layer_change(self, _event=None) -> None:
        """Synchronize controls after programmatic layer changes."""
        with qt_signals_blocked(self.orientation_combobox):
            self.orientation_combobox.setCurrentText(self.layer.orientation.value)
        with qt_signals_blocked(self.baseline_spinbox):
            self.baseline_spinbox.setValue(self.layer.baseline)
        with qt_signals_blocked(self.width_spinbox):
            self.width_spinbox.setValue(self.layer.width)
        with qt_signals_blocked(self.border_width_spinbox):
            self.border_width_spinbox.setValue(self.layer.border_width)
        if len(self.layer.fill_color):
            with qt_signals_blocked(self.fill_color_swatch):
                self.fill_color_swatch.setColor(self.layer.fill_color[0])
        if len(self.layer.border_color):
            with qt_signals_blocked(self.border_color_swatch):
                self.border_color_swatch.setColor(self.layer.border_color[0])

    def _on_visible_change(self, _event=None) -> None:
        """Enable controls only while the layer is visible."""
        set_widgets_enabled_with_opacity(
            self,
            [
                self.orientation_combobox,
                self.baseline_spinbox,
                self.width_spinbox,
                self.fill_color_swatch,
                self.border_color_swatch,
                self.border_width_spinbox,
                self.opacity_slider,
                self.blending_combobox,
            ],
            self.layer.visible,
        )


__all__ = ["QtBarControls"]
