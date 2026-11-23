"""Appearance controls for areas, bands and error bars."""

from __future__ import annotations

from typing import TYPE_CHECKING

import qtextra.helpers as hp
from napari._qt.utils import qt_signals_blocked

from napari_plot._qt.layer_controls.qt_layer_controls_base import QtLayerControls
from napari_plot.layers.areas import AreasOrientation

if TYPE_CHECKING:
    import numpy as np

    from napari_plot.layers import Areas, Band, ErrorBar


class QtAreasControls(QtLayerControls):
    """Edit area orientation, fill, and outlines."""

    layer: Areas

    def __init__(self, layer: Areas) -> None:
        super().__init__(layer)
        self.orientation_combobox = hp.make_combobox(
            self, items=[str(orientation) for orientation in AreasOrientation], value=str(layer.orientation)
        )
        self.orientation_combobox.currentTextChanged.connect(self._set_orientation)
        self.fill_color_swatch = hp.make_swatch(
            self, layer.fill_color[0] if len(layer.data) else "white", func=self._set_fill_color
        )
        self.border_color_swatch = hp.make_swatch(
            self, layer.border_color[0] if len(layer.data) else "dimgray", func=self._set_border_color
        )
        self.border_width_spinbox = hp.make_double_spin_box(
            self,
            minimum=0,
            maximum=20,
            n_decimals=1,
            step_size=0.5,
            value=layer.border_width,
            func=self._set_border_width,
        )
        layer.events.orientation.connect(self._on_orientation_change)
        layer.events.fill_color.connect(self._on_color_change)
        layer.events.border_color.connect(self._on_color_change)
        layer.events.data.connect(self._on_color_change)
        layer.events.border_width.connect(self._on_border_width_change)

        self.layout().addRow(self.button_grid)
        self.layout().addRow(self.opacity_label, self.opacity_slider)
        self.layout().addRow(hp.make_label(self, "blending"), self.blending_combobox)
        self.layout().addRow(hp.make_label(self, "orientation"), self.orientation_combobox)
        self.layout().addRow(hp.make_label(self, "fill color"), self.fill_color_swatch)
        self.layout().addRow(hp.make_label(self, "border color"), self.border_color_swatch)
        self.layout().addRow(hp.make_label(self, "border width (px)"), self.border_width_spinbox)
        self._on_color_change()

    def _set_orientation(self, value: str) -> None:
        self.layer.orientation = value

    def _on_orientation_change(self) -> None:
        with qt_signals_blocked(self.orientation_combobox):
            self.orientation_combobox.setCurrentText(str(self.layer.orientation))

    def _set_fill_color(self, value: np.ndarray) -> None:
        self.layer.fill_color = value

    def _set_border_color(self, value: np.ndarray) -> None:
        self.layer.border_color = value

    def _on_color_change(self) -> None:
        self.fill_color_swatch.setEnabled(bool(self.layer.data))
        self.border_color_swatch.setEnabled(bool(self.layer.data))
        if self.layer.data:
            with qt_signals_blocked(self.fill_color_swatch):
                self.fill_color_swatch.set_color(self.layer.fill_color[0], force=True)
            with qt_signals_blocked(self.border_color_swatch):
                self.border_color_swatch.set_color(self.layer.border_color[0], force=True)

    def _set_border_width(self, value: float) -> None:
        self.layer.border_width = value

    def _on_border_width_change(self) -> None:
        with qt_signals_blocked(self.border_width_spinbox):
            self.border_width_spinbox.setValue(self.layer.border_width)


class QtBandControls(QtLayerControls):
    """Edit band color, opacity, and blending."""

    layer: Band

    def __init__(self, layer: Band) -> None:
        super().__init__(layer)
        self.fill_color_swatch = hp.make_swatch(self, layer.fill_color, func=self._set_fill_color)
        layer.events.fill_color.connect(self._on_fill_color_change)

        self.layout().addRow(self.button_grid)
        self.layout().addRow(self.opacity_label, self.opacity_slider)
        self.layout().addRow(hp.make_label(self, "blending"), self.blending_combobox)
        self.layout().addRow(hp.make_label(self, "fill color"), self.fill_color_swatch)

    def _set_fill_color(self, value: np.ndarray) -> None:
        self.layer.fill_color = value

    def _on_fill_color_change(self) -> None:
        with qt_signals_blocked(self.fill_color_swatch):
            self.fill_color_swatch.set_color(self.layer.fill_color, force=True)


class QtErrorBarControls(QtLayerControls):
    """Edit the appearance of error bar stems and caps."""

    layer: ErrorBar

    def __init__(self, layer: ErrorBar) -> None:
        super().__init__(layer)
        self.color_swatch = hp.make_swatch(self, layer.color, func=self._set_color)
        self.width_spinbox = hp.make_double_spin_box(
            self, minimum=0.01, maximum=20, n_decimals=1, step_size=0.5, value=layer.width, func=self._set_width
        )
        self.cap_size_spinbox = hp.make_double_spin_box(
            self, minimum=0, maximum=20, n_decimals=1, step_size=0.5, value=layer.cap_size, func=self._set_cap_size
        )
        layer.events.color.connect(self._on_color_change)
        layer.events.width.connect(self._on_width_change)
        layer.events.cap_size.connect(self._on_cap_size_change)

        self.layout().addRow(self.button_grid)
        self.layout().addRow(self.opacity_label, self.opacity_slider)
        self.layout().addRow(hp.make_label(self, "blending"), self.blending_combobox)
        self.layout().addRow(hp.make_label(self, "color"), self.color_swatch)
        self.layout().addRow(hp.make_label(self, "line width (px)"), self.width_spinbox)
        self.layout().addRow(hp.make_label(self, "cap size (px)"), self.cap_size_spinbox)

    def _set_color(self, value: np.ndarray) -> None:
        self.layer.color = value

    def _set_width(self, value: float) -> None:
        self.layer.width = value

    def _set_cap_size(self, value: float) -> None:
        self.layer.cap_size = value

    def _on_color_change(self) -> None:
        with qt_signals_blocked(self.color_swatch):
            self.color_swatch.set_color(self.layer.color, force=True)

    def _on_width_change(self) -> None:
        with qt_signals_blocked(self.width_spinbox):
            self.width_spinbox.setValue(self.layer.width)

    def _on_cap_size_change(self) -> None:
        with qt_signals_blocked(self.cap_size_spinbox):
            self.cap_size_spinbox.setValue(self.layer.cap_size)
