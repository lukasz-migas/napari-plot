"""Controls for the plot grid lines overlay."""

from __future__ import annotations

import typing as ty
from contextlib import ExitStack

import numpy as np
import qtextra.helpers as hp
from napari._qt.utils import qt_signals_blocked
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from qtextra.widgets.qt_dialog import QtFramelessPopup
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout, QWidget

from napari_plot._vispy.overlays.grid_lines import auto_grid_color

if ty.TYPE_CHECKING:
    from napari_plot.components.viewer_model import ViewerModel


class QtGridLinesControls(QtFramelessPopup):
    """Popup for grid line visibility, color, opacity, width and minor lines."""

    def __init__(self, viewer: ViewerModel, parent: QWidget | None = None) -> None:
        self.viewer = viewer
        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("grid_lines")
        self.setMouseTracking(True)

        overlay = viewer.grid_lines
        connections = self._overlay_connections = ExitStack()
        for signal, callback in (
            (overlay.events.visible, self._on_visible_change),
            (overlay.events.color, self._on_color_change),
            (overlay.events.opacity, self._on_opacity_change),
            (overlay.events.width, self._on_width_change),
            (overlay.events.minor, self._on_minor_change),
            (viewer.canvas.events.background_color, self._on_color_change),
        ):
            signal.connect(callback)
            connections.callback(signal.disconnect, callback)
        self.destroyed.connect(lambda *_args: connections.close())

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Create the popup form."""
        overlay = self.viewer.grid_lines
        self.visible_checkbox = hp.make_checkbox(
            self, "", value=overlay.visible, tooltip="Show or hide the grid lines.", func=self.on_change_visible
        )
        self.auto_color_checkbox = hp.make_checkbox(
            self,
            "",
            value=overlay.color is None,
            tooltip="Pick black or white automatically, whichever contrasts more with the canvas background.",
            func=self.on_change_auto_color,
        )
        self.color_swatch = QColorSwatchEdit(self, initial_color=self._display_color())
        self.color_swatch.setEnabled(overlay.color is not None)
        self.color_swatch.color_changed.connect(self.on_change_color)
        self.opacity_slider = hp.make_double_slider_with_text(
            self, 0, 1, step_size=0.05, n_decimals=2, value=overlay.opacity, func=self.on_change_opacity
        )
        self.width_slider = hp.make_double_slider_with_text(
            self, 0.5, 5, step_size=0.5, value=overlay.width, func=self.on_change_width
        )
        self.minor_checkbox = hp.make_checkbox(
            self, "", value=overlay.minor, tooltip="Also draw lines at the minor ticks.", func=self.on_change_minor
        )

        layout = hp.make_form_layout(parent=self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addRow(self._make_move_handle("Grid line controls"))
        layout.addRow(hp.make_label(self, "Visible"), self.visible_checkbox)
        layout.addRow(hp.make_label(self, "Auto color"), self.auto_color_checkbox)
        layout.addRow(hp.make_label(self, "Color"), self.color_swatch)
        layout.addRow(hp.make_label(self, "Opacity"), self.opacity_slider)
        layout.addRow(hp.make_label(self, "Width"), self.width_slider)
        layout.addRow(hp.make_label(self, "Minor lines"), self.minor_checkbox)
        layout.setSpacing(2)
        return layout

    def _display_color(self) -> np.ndarray:
        """Return the explicit color, or the automatic one for the current canvas background."""
        color = self.viewer.grid_lines.color
        return np.asarray(auto_grid_color(self.viewer.canvas.background_color) if color is None else color)

    def on_change_visible(self) -> None:
        """Update grid line visibility."""
        self.viewer.grid_lines.visible = self.visible_checkbox.isChecked()

    def _on_visible_change(self, _event: object = None) -> None:
        with qt_signals_blocked(self.visible_checkbox):
            self.visible_checkbox.setChecked(self.viewer.grid_lines.visible)

    def on_change_auto_color(self) -> None:
        """Switch between the automatic color and the color in the swatch."""
        auto = self.auto_color_checkbox.isChecked()
        self.viewer.grid_lines.color = None if auto else self.color_swatch.color

    def on_change_color(self, color: np.ndarray) -> None:
        """Set an explicit grid line color."""
        if not self.auto_color_checkbox.isChecked():
            self.viewer.grid_lines.color = color

    def _on_color_change(self, _event: object = None) -> None:
        auto = self.viewer.grid_lines.color is None
        with qt_signals_blocked(self.auto_color_checkbox):
            self.auto_color_checkbox.setChecked(auto)
        with qt_signals_blocked(self.color_swatch):
            self.color_swatch.setColor(self._display_color())
        self.color_swatch.setEnabled(not auto)

    def on_change_opacity(self) -> None:
        """Update grid line opacity."""
        self.viewer.grid_lines.opacity = self.opacity_slider.value()

    def _on_opacity_change(self, _event: object = None) -> None:
        with qt_signals_blocked(self.opacity_slider):
            self.opacity_slider.setValue(self.viewer.grid_lines.opacity)

    def on_change_width(self) -> None:
        """Update grid line width."""
        self.viewer.grid_lines.width = self.width_slider.value()

    def _on_width_change(self, _event: object = None) -> None:
        with qt_signals_blocked(self.width_slider):
            self.width_slider.setValue(self.viewer.grid_lines.width)

    def on_change_minor(self) -> None:
        """Toggle lines at the minor ticks."""
        self.viewer.grid_lines.minor = self.minor_checkbox.isChecked()

    def _on_minor_change(self, _event: object = None) -> None:
        with qt_signals_blocked(self.minor_checkbox):
            self.minor_checkbox.setChecked(self.viewer.grid_lines.minor)

    def _on_teardown(self) -> None:
        """Disconnect overlay and canvas events when the popup closes."""
        self._overlay_connections.close()


__all__ = ["QtGridLinesControls"]
