"""Controls for the canvas legend overlay."""

from __future__ import annotations

import typing as ty

import numpy as np
import qtextra.helpers as hp
from napari._qt.utils import qt_signals_blocked
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from napari.components._viewer_constants import CanvasPosition
from napari.utils.events import disconnect_events
from qtextra.widgets.qt_dialog import QtFramelessPopup
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout

if ty.TYPE_CHECKING:
    from napari_plot.components.viewer_model import ViewerModel

POSITION_TRANSLATIONS = {
    CanvasPosition.TOP_LEFT: "Top left",
    CanvasPosition.TOP_CENTER: "Top center",
    CanvasPosition.TOP_RIGHT: "Top right",
    CanvasPosition.BOTTOM_RIGHT: "Bottom right",
    CanvasPosition.BOTTOM_CENTER: "Bottom center",
    CanvasPosition.BOTTOM_LEFT: "Bottom left",
}


class QtLegendControls(QtFramelessPopup):
    """Popup for legend visibility, placement, synchronization, and style."""

    def __init__(self, viewer: ViewerModel, parent=None) -> None:
        self.viewer = viewer
        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("legend")
        self.setMouseTracking(True)

        overlay = viewer.legend
        overlay.events.visible.connect(self._on_visible_change)
        overlay.events.position.connect(self._on_position_change)
        overlay.events.sync_with_source.connect(self._on_auto_sync_change)
        overlay.events.text_color.connect(self._on_text_color_change)
        overlay.events.font_size.connect(self._on_font_size_change)
        overlay.events.marker_size.connect(self._on_marker_size_change)
        overlay.events.row_spacing.connect(self._on_row_spacing_change)
        overlay.events.padding.connect(self._on_padding_change)
        overlay.events.background_color.connect(self._on_background_color_change)
        overlay.events.border_color.connect(self._on_border_color_change)
        overlay.events.border_width.connect(self._on_border_width_change)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Create the popup form."""
        overlay = self.viewer.legend
        self.visible_checkbox = hp.make_checkbox(
            self,
            "",
            value=overlay.visible,
            tooltip="Show or hide the legend.",
            func=self.on_change_visible,
        )
        self.position_combobox = hp.make_combobox(self)
        hp.set_combobox_data(self.position_combobox, POSITION_TRANSLATIONS, overlay.position)
        self.position_combobox.currentIndexChanged.connect(self.on_change_position)
        self.auto_sync_checkbox = hp.make_checkbox(
            self,
            "",
            value=overlay.sync_with_source,
            tooltip="Refresh entries when plot layers change.",
            func=self.on_change_auto_sync,
        )
        self.refresh_button = hp.make_btn(
            self,
            "Refresh",
            tooltip="Regenerate entries from the configured source.",
            func=self.viewer.refresh_legend_from_source,
        )
        self.text_color_swatch = QColorSwatchEdit(self, initial_color=overlay.text_color)
        self.text_color_swatch.color_changed.connect(self.on_change_text_color)
        self.background_color_swatch = QColorSwatchEdit(self, initial_color=overlay.background_color)
        self.background_color_swatch.color_changed.connect(self.on_change_background_color)
        self.border_color_swatch = QColorSwatchEdit(self, initial_color=overlay.border_color)
        self.border_color_swatch.color_changed.connect(self.on_change_border_color)
        self.font_size_spinbox = hp.make_double_slider_with_text(
            self,
            4,
            32,
            step_size=1,
            value=overlay.font_size,
            func=self.on_change_font_size,
        )
        self.marker_size_spinbox = hp.make_double_slider_with_text(
            self,
            4,
            32,
            step_size=1,
            value=overlay.marker_size,
            func=self.on_change_marker_size,
        )
        self.padding_spinbox = hp.make_double_slider_with_text(
            self,
            0,
            24,
            step_size=1,
            value=overlay.padding,
            func=self.on_change_padding,
        )
        self.row_spacing_spinbox = hp.make_double_slider_with_text(
            self,
            1,
            24,
            step_size=1,
            value=overlay.row_spacing,
            func=self.on_change_row_spacing,
        )
        self.border_width_spinbox = hp.make_double_slider_with_text(
            self,
            0,
            8,
            step_size=0.5,
            value=overlay.border_width,
            func=self.on_change_border_width,
        )

        layout = hp.make_form_layout(parent=self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addRow(self._make_move_handle("Legend controls"))
        layout.addRow(hp.make_label(self, "Visible"), self.visible_checkbox)
        layout.addRow(hp.make_label(self, "Position"), self.position_combobox)
        layout.addRow(hp.make_label(self, "Auto sync"), self.auto_sync_checkbox)
        layout.addRow(hp.make_label(self, "Entries"), self.refresh_button)
        layout.addRow(hp.make_label(self, "Text color"), self.text_color_swatch)
        layout.addRow(hp.make_label(self, "Text size"), self.font_size_spinbox)
        layout.addRow(hp.make_label(self, "Marker size"), self.marker_size_spinbox)
        layout.addRow(hp.make_label(self, "Padding"), self.padding_spinbox)
        layout.addRow(hp.make_label(self, "Row gap"), self.row_spacing_spinbox)
        layout.addRow(hp.make_label(self, "Background"), self.background_color_swatch)
        layout.addRow(hp.make_label(self, "Border color"), self.border_color_swatch)
        layout.addRow(hp.make_label(self, "Border width"), self.border_width_spinbox)
        layout.setSpacing(2)
        return layout

    def on_change_visible(self) -> None:
        """Update legend visibility."""
        self.viewer.legend.visible = self.visible_checkbox.isChecked()

    def _on_visible_change(self, _event=None) -> None:
        with qt_signals_blocked(self.visible_checkbox):
            self.visible_checkbox.setChecked(self.viewer.legend.visible)

    def on_change_position(self) -> None:
        """Update legend canvas position."""
        self.viewer.legend.position = self.position_combobox.currentData()

    def _on_position_change(self, _event=None) -> None:
        with qt_signals_blocked(self.position_combobox):
            hp.set_combobox_current_index(self.position_combobox, self.viewer.legend.position)

    def on_change_auto_sync(self) -> None:
        """Update automatic layer synchronization."""
        self.viewer.set_legend_auto_sync(self.auto_sync_checkbox.isChecked())

    def _on_auto_sync_change(self, _event=None) -> None:
        with qt_signals_blocked(self.auto_sync_checkbox):
            self.auto_sync_checkbox.setChecked(self.viewer.legend.sync_with_source)

    def on_change_text_color(self, color: np.ndarray) -> None:
        """Update legend text color."""
        self.viewer.legend.text_color = color

    def _on_text_color_change(self, _event=None) -> None:
        with qt_signals_blocked(self.text_color_swatch):
            self.text_color_swatch.setColor(self.viewer.legend.text_color)

    def on_change_background_color(self, color: np.ndarray) -> None:
        """Update legend background color."""
        self.viewer.legend.background_color = color

    def _on_background_color_change(self, _event=None) -> None:
        with qt_signals_blocked(self.background_color_swatch):
            self.background_color_swatch.setColor(self.viewer.legend.background_color)

    def on_change_border_color(self, color: np.ndarray) -> None:
        """Update legend border color."""
        self.viewer.legend.border_color = color

    def _on_border_color_change(self, _event=None) -> None:
        with qt_signals_blocked(self.border_color_swatch):
            self.border_color_swatch.setColor(self.viewer.legend.border_color)

    def on_change_font_size(self) -> None:
        """Update legend font size."""
        self.viewer.legend.font_size = self.font_size_spinbox.value()

    def _on_font_size_change(self, _event=None) -> None:
        with qt_signals_blocked(self.font_size_spinbox):
            self.font_size_spinbox.setValue(self.viewer.legend.font_size)

    def on_change_marker_size(self) -> None:
        """Update legend marker size."""
        self.viewer.legend.marker_size = self.marker_size_spinbox.value()

    def _on_marker_size_change(self, _event=None) -> None:
        with qt_signals_blocked(self.marker_size_spinbox):
            self.marker_size_spinbox.setValue(self.viewer.legend.marker_size)

    def on_change_padding(self) -> None:
        """Update legend padding."""
        self.viewer.legend.padding = self.padding_spinbox.value()

    def _on_padding_change(self, _event=None) -> None:
        with qt_signals_blocked(self.padding_spinbox):
            self.padding_spinbox.setValue(self.viewer.legend.padding)

    def on_change_row_spacing(self) -> None:
        """Update legend row spacing."""
        self.viewer.legend.row_spacing = self.row_spacing_spinbox.value()

    def _on_row_spacing_change(self, _event=None) -> None:
        with qt_signals_blocked(self.row_spacing_spinbox):
            self.row_spacing_spinbox.setValue(self.viewer.legend.row_spacing)

    def on_change_border_width(self) -> None:
        """Update legend border width."""
        self.viewer.legend.border_width = self.border_width_spinbox.value()

    def _on_border_width_change(self, _event=None) -> None:
        with qt_signals_blocked(self.border_width_spinbox):
            self.border_width_spinbox.setValue(self.viewer.legend.border_width)

    def close(self) -> None:
        """Disconnect overlay events before closing."""
        disconnect_events(self.viewer.legend.events, self)
        super().close()


__all__ = ["QtLegendControls"]
