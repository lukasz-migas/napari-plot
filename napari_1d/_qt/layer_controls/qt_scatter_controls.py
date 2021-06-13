"""Scatter layer controls"""
from typing import TYPE_CHECKING

import numpy as np
from napari._qt.utils import disable_with_opacity, qt_signals_blocked
from napari._qt.widgets.qt_color_swatch import QColorSwatch
from napari.layers.points._points_constants import SYMBOL_TRANSLATION
from napari.utils.events import disconnect_events
from qtpy.QtCore import Qt, Slot

from ..helpers import (
    make_checkbox,
    make_combobox,
    make_label,
    make_slider,
    set_combobox_data,
    set_current_combobox_index,
)
from .qt_layer_controls_base import QtLayerControls

if TYPE_CHECKING:
    from ...layers import Scatter


class QtScatterControls(QtLayerControls):
    """Qt view and controls for the napari_1d Scatter layer.

    Parameters
    ----------
    layer : napari_1d.layers.Scatter
        An instance of a imimsui Scatter layer.

    Attributes
    ----------
    layer : napari.layers.Points
        An instance of a napari Points layer.
    edge_color_swatch : qtpy.QtWidgets.QFrame
        Color swatch showing shapes edge display color.
    face_color_swatch : qtpy.QtWidgets.QFrame
        Color swatch showing shapes face display color.
    size_slider : qtpy.QtWidgets.QSlider
        Slider controlling size of points.
    symbol_combobox : qtpy.QtWidgets.QComboBox
        Drop down list of symbol options for points markers.
    scaling_checkbox : qtpy.QtWidgets.QCheckBox
        Checkbox to enable/disable scaling of scatter points
    text_display_checkbox : qtpy.QtWidgets.QCheckBox
        Checkbox to enable/disable visibility of text items
    """

    def __init__(self, layer: "Scatter"):
        super().__init__(layer)

        self.layer.events.symbol.connect(self._on_symbol_change)
        self.layer.events.size.connect(self._on_size_change)
        self.layer.events.edge_width.connect(self._on_edge_width_change)
        self.layer.events.face_color.connect(self._on_face_color_change)
        self.layer.events.edge_color.connect(self._on_edge_color_change)
        self.layer.events.scaling.connect(self._on_scaling_change)
        self.layer.text.events.visible.connect(self._on_text_visibility_change)
        self.layer.events.editable.connect(self._on_editable_change)

        self.size_slider = make_slider(self, 1, tooltip="Scatter point size")
        self.size_slider.setFocusPolicy(Qt.NoFocus)
        self.size_slider.setValue(int(self.layer.size))
        self.size_slider.valueChanged.connect(self.on_change_size)

        self.face_color_swatch = QColorSwatch(
            initial_color=self.layer.face_color,
            tooltip="Click to set face color",
        )
        self.face_color_swatch.color_changed.connect(self.on_change_face_color)  # noqa

        self.edge_color_swatch = QColorSwatch(
            initial_color=self.layer.edge_color,
            tooltip="Click to set edge color",
        )
        self.edge_color_swatch.color_changed.connect(self.on_change_edge_color)  # noqa

        self.edge_width_slider = make_slider(self, 1, tooltip="Scatter edge width")
        self.edge_width_slider.setFocusPolicy(Qt.NoFocus)
        self.edge_width_slider.setValue(int(self.layer.edge_width))
        self.edge_width_slider.valueChanged.connect(self.on_change_edge_width)

        self.symbol_combobox = make_combobox(self, tooltip="Marker symbol")
        set_combobox_data(self.symbol_combobox, SYMBOL_TRANSLATION, self.layer.symbol)
        self.symbol_combobox.activated[str].connect(self.on_change_symbol)

        self.scaling_checkbox = make_checkbox(self, tooltip="Scale scatter points with zoom")
        self.scaling_checkbox.setChecked(self.layer.scaling)
        self.scaling_checkbox.stateChanged.connect(self.on_change_scaling)

        self.text_display_checkbox = make_checkbox(self, tooltip="Toggle text visibility")
        self.text_display_checkbox.setChecked(self.layer.text.visible)
        self.text_display_checkbox.stateChanged.connect(self.on_change_text_visibility)

        # grid_layout created in QtLayerControls
        self.layout.addRow(make_label(self, "Opacity"), self.opacity_slider)
        self.layout.addRow(make_label(self, "Points size"), self.size_slider)
        self.layout.addRow(make_label(self, "Blending"), self.blending_combobox)
        self.layout.addRow(make_label(self, "Symbol"), self.symbol_combobox)
        self.layout.addRow(make_label(self, "Face color"), self.face_color_swatch)
        self.layout.addRow(make_label(self, "Edge color"), self.edge_color_swatch)
        self.layout.addRow(make_label(self, "Edge width"), self.edge_width_slider)
        self.layout.addRow(make_label(self, "Scaling"), self.scaling_checkbox)
        self.layout.addRow(make_label(self, "Display text"), self.text_display_checkbox)
        self.layout.addRow(make_label(self, "Editable"), self.editable_checkbox)
        self._on_editable_change()

    def on_change_symbol(self, _text):
        """Change marker symbol of the points on the layer model.

        Parameters
        ----------
        _text : int
            Index of current marker symbol of points, eg: '+', '.', etc.
        """
        self.layer.symbol = self.symbol_combobox.currentData()

    def _on_symbol_change(self, _event):
        """Receive marker symbol change event and update the dropdown menu.

        Parameters
        ----------
        _event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        with self.layer.events.symbol.blocker():
            set_current_combobox_index(self.symbol_combobox, self.layer.symbol)

    def on_change_size(self, value):
        """Change size of points on the layer model.

        Parameters
        ----------
        value : float
            Size of points.
        """
        self.layer.size = value

    def _on_size_change(self, _event):
        """Receive layer model size change event and update point size slider.

        Parameters
        ----------
        _event : napari.utils.event.Event, optional
            The napari event that triggered this method.
        """
        with self.layer.events.size.blocker():
            self.size_slider.setValue(int(self.layer.size))

    def on_change_edge_width(self, value):
        """Change size of points on the layer model.

        Parameters
        ----------
        value : float
            Size of points.
        """
        self.layer.edge_width = value

    def _on_edge_width_change(self, _event):
        """Receive layer model size change event and update point size slider.

        Parameters
        ----------
        _event : napari.utils.event.Event, optional
            The napari event that triggered this method.
        """
        with self.layer.events.edge_width.blocker():
            self.edge_width_slider.setValue(int(self.layer.edge_width))

    def on_change_text_visibility(self, state):
        """Toggle the visibility of the text.

        Parameters
        ----------
        state : QCheckBox
            Checkbox indicating if text is visible.
        """
        self.layer.text.visible = state == Qt.Checked

    def _on_text_visibility_change(self, _event):
        """Receive layer model text visibility change change event and update checkbox.

        Parameters
        ----------
        _event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        with self.layer.text.events.visible.blocker():
            self.text_display_checkbox.setChecked(self.layer.text.visible)

    def on_change_scaling(self, state):
        """Toggle the visibility of the text.

        Parameters
        ----------
        state : QCheckBox
            Checkbox indicating if text is visible.
        """
        self.layer.scaling = state == Qt.Checked

    def _on_scaling_change(self, _event):
        """Receive layer model text visibility change change event and update checkbox.

        Parameters
        ----------
        _event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        with self.layer.events.scaling.blocker():
            self.scaling_checkbox.setChecked(self.layer.scaling)

    @Slot(np.ndarray)  # noqa
    def on_change_face_color(self, color: np.ndarray):
        """Update face color of layer model from color picker user input."""
        self.layer.face_color = color

    def _on_face_color_change(self, _event):
        """Receive layer.current_face_color() change event and update view."""
        with qt_signals_blocked(self.face_color_swatch):
            self.face_color_swatch.setColor(self.layer.face_color)

    @Slot(np.ndarray)  # noqa
    def on_change_edge_color(self, color: np.ndarray):
        """Update edge color of layer model from color picker user input."""
        self.layer.edge_color = color

    def _on_edge_color_change(self, _event):
        """Receive layer.current_edge_color() change event and update view."""
        with qt_signals_blocked(self.edge_color_swatch):
            self.edge_color_swatch.setColor(self.layer.edge_color)

    def _on_editable_change(self, event=None):
        """Receive layer model editable change event & enable/disable buttons.

        Parameters
        ----------
        event : napari.utils.event.Event, optional
            The napari event that triggered this method, by default None.
        """
        disable_with_opacity(
            self,
            [
                "scaling_checkbox",
                "text_display_checkbox",
                "face_color_swatch",
                "edge_color_swatch",
                "size_slider",
                "opacity_slider",
                "blending_combobox",
                "edge_width_slider",
                "symbol_combobox",
            ],
            not self.layer.editable,
        )
        super()._on_editable_change()

    def close(self):
        """Disconnect events when widget is closing."""
        disconnect_events(self.layer.text.events, self)
        super().close()
