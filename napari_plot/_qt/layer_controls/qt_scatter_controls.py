"""Scatter layer controls"""

import contextlib
import typing as ty

import numpy as np
import qtextra.helpers as hp
from napari._qt.utils import qt_signals_blocked, set_widgets_enabled_with_opacity
from napari._qt.widgets.qt_color_swatch import QColorSwatch
from napari.layers.points._points_constants import SYMBOL_TRANSLATION
from napari.utils.events import disconnect_events
from qtpy.QtCore import Qt, Slot

from napari_plot._qt.layer_controls.qt_layer_controls_base import QtLayerControls

if ty.TYPE_CHECKING:
    from napari_plot.layers import Scatter


class QtScatterControls(QtLayerControls):
    """Qt view and controls for the napari_plot Scatter layer.

    Parameters
    ----------
    layer : napari_plot.layers.Scatter
        An instance of a Scatter layer.

    Attributes
    ----------
    layer : napari_plot.layers.Scatter
        An instance of a Scatter layer.
    layout : qtpy.QtWidgets.QFormLayout
        Layout of Qt widget controls for the layer.
    editable_checkbox : qtpy.QtWidgets.QCheckBox
        Checkbox widget to control editability of the layer.
    blending_combobox : qtpy.QtWidgets.QComboBox
        Dropdown widget to select blending mode of layer.
    opacity_slider : qtpy.QtWidgets.QSlider
        Slider controlling opacity of the layer.
    edge_color_swatch : qtpy.QtWidgets.QFrame
        Color swatch showing shapes edge display color.
    size_slider : qtpy.QtWidgets.QSlider
        Slider controlling size of points.
    face_color_swatch : qtpy.QtWidgets.QFrame
        Color swatch showing shapes face display color.
    symbol_combobox : qtpy.QtWidgets.QComboBox
        Drop down list of symbol options for points markers.
    scaling_checkbox : qtpy.QtWidgets.QCheckBox
        Checkbox to enable/disable scaling of scatter points
    text_display_checkbox : qtpy.QtWidgets.QCheckBox
        Checkbox to enable/disable visibility of text items
    """

    PAN_ZOOM_ACTION_NAME = "activate_scatter_pan_zoom_mode"
    TRANSFORM_ACTION_NAME = "activate_scatter_transform_mode"

    def __init__(self, layer: "Scatter"):
        super().__init__(layer)
        self.layer.events.symbol.connect(self._on_symbol_change)
        self.layer.events.size.connect(self._on_size_change)
        self.layer.events.border_width.connect(self._on_edge_width_change)
        self.layer.events.face_color.connect(self._on_face_color_change)
        self.layer.events.border_color.connect(self._on_edge_color_change)
        self.layer.events.border_width_is_relative.connect(self._on_edge_width_is_relative_change)
        self.layer.events.scaling.connect(self._on_scaling_change)
        self.layer.text.events.visible.connect(self._on_text_visibility_change)
        self.layer.events.editable.connect(self._on_editable_or_visible_change)
        self.layer.events.visible.connect(self._on_editable_or_visible_change)

        self.size_slider = hp.make_slider_with_text(
            self,
            1,
            tooltip="Scatter point size",
            focus_policy=Qt.FocusPolicy.NoFocus,
        )
        self.size_slider.valueChanged.connect(self.on_change_size)

        self.face_color_swatch = QColorSwatch(
            initial_color=self.layer.face_color[-1]
            if self.layer.face_color.size > 0
            else self.layer._default_face_color,
            tooltip="Click to set face color",
        )
        self.face_color_swatch.color_changed.connect(self.on_change_face_color)

        self.border_color_swatch = QColorSwatch(
            initial_color=self.layer.border_color[-1]
            if self.layer.border_color.size > 0
            else self.layer._default_border_color,
            tooltip="Click to set edge color",
        )
        self.border_color_swatch.color_changed.connect(self.on_change_edge_color)

        self.border_width_relative = hp.make_checkbox(
            self,
            val=self.layer.border_width_is_relative,
            tooltip="Toggle between relative and absolute edge widths.",
        )
        self.border_width_relative.stateChanged.connect(self.on_change_edge_width_is_relative)

        self.border_width_slider = hp.make_double_slider_with_text(
            self,
            1,
            tooltip="Scatter edge width",
            focus_policy=Qt.FocusPolicy.NoFocus,
        )
        self.border_width_slider.valueChanged.connect(self.on_change_edge_width)

        self.symbol_combobox = hp.make_combobox(self, tooltip="Marker symbol")
        current_symbol = self.layer.symbol[-1] if len(self.layer.symbol) > 0 else None
        hp.set_combobox_data(self.symbol_combobox, SYMBOL_TRANSLATION, current_symbol)
        self.symbol_combobox.currentTextChanged.connect(self.on_change_symbol)

        self.scaling_checkbox = hp.make_checkbox(self, val=self.layer.scaling, tooltip="Scale scatter points with zoom")
        self.scaling_checkbox.stateChanged.connect(self.on_change_scaling)

        self.text_display_checkbox = hp.make_checkbox(
            self, val=self.layer.text.visible, tooltip="Toggle text visibility"
        )
        self.text_display_checkbox.stateChanged.connect(self.on_change_text_visibility)

        # add widgets to the layout
        self.layout().addRow(self.button_grid)
        self.layout().addRow(self.opacity_label, self.opacity_slider)
        self.layout().addRow(hp.make_label(self, "Points size"), self.size_slider)
        self.layout().addRow(hp.make_label(self, "Blending"), self.blending_combobox)
        self.layout().addRow(hp.make_label(self, "Symbol"), self.symbol_combobox)
        self.layout().addRow(hp.make_label(self, "Face color"), self.face_color_swatch)
        self.layout().addRow(hp.make_label(self, "Border color"), self.border_color_swatch)
        self.layout().addRow(
            hp.make_label(self, "Rel. border width", tooltip="Border width is relative"),
            self.border_width_relative,
        )
        self.layout().addRow(hp.make_label(self, "Border width"), self.border_width_slider)
        self.layout().addRow(hp.make_label(self, "Scaling"), self.scaling_checkbox)
        self.layout().addRow(hp.make_label(self, "Display text"), self.text_display_checkbox)
        self.layout().addRow(hp.make_label(self, "Editable"), self.editable_checkbox)

        # initialize values
        self._on_size_change(None)
        self._on_edge_width_is_relative_change(None)
        self._on_edge_width_change(None)
        self._on_editable_or_visible_change(None)

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
            current_symbol = self.layer.symbol[-1] if len(self.layer.symbol) > 0 else None
            hp.set_combobox_current_index(self.symbol_combobox, current_symbol)

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
            with self.layer.events.size.blocker():
                value = self.layer.current_size
                min_val = min(value) if isinstance(value, list) else value
                max_val = max(value) if isinstance(value, list) else value
                if min_val < self.size_slider.minimum():
                    self.size_slider.setMinimum(max(1, int(min_val - 1)))
                if max_val > self.size_slider.maximum():
                    self.size_slider.setMaximum(int(max_val + 1))
                with contextlib.suppress(TypeError):
                    self.size_slider.setValue(int(value))

    def on_change_edge_width(self, value):
        """Change size of points on the layer model.

        Parameters
        ----------
        value : float
            Size of points.
        """
        self.layer.border_width = value

    def _on_edge_width_change(self, _event):
        """Receive layer model size change event and update point size slider.

        Parameters
        ----------
        _event : napari.utils.event.Event, optional
            The napari event that triggered this method.
        """
        with self.layer.events.border_width.blocker():
            edge_width = (
                self.layer.border_width[-1] if len(self.layer.border_width) > 0 else self.layer._default_border_width
            )
            self.border_width_slider.setValue(edge_width)

    def on_change_text_visibility(self, state):
        """Toggle the visibility of the text.

        Parameters
        ----------
        state : QCheckBox
            Checkbox indicating if text is visible.
        """
        self.layer.text.visible = state == Qt.CheckState.Checked

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
        self.layer.scaling = state == Qt.CheckState.Checked

    def _on_scaling_change(self, _event):
        """Receive layer model text visibility change change event and update checkbox.

        Parameters
        ----------
        _event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        with self.layer.events.scaling.blocker():
            self.scaling_checkbox.setChecked(self.layer.scaling)

    @Slot(np.ndarray)
    def on_change_face_color(self, color: np.ndarray):
        """Update face color of layer model from color picker user input."""
        self.layer.face_color = color

    def _on_face_color_change(self, _event):
        """Receive layer.current_face_color() change event and update view."""
        with qt_signals_blocked(self.face_color_swatch):
            self.face_color_swatch.setColor(
                self.layer.face_color[-1] if self.layer.face_color.size > 0 else self.layer._default_face_color
            )

    @Slot(np.ndarray)
    def on_change_edge_color(self, color: np.ndarray):
        """Update edge color of layer model from color picker user input."""
        self.layer.border_color = color

    def _on_edge_color_change(self, _event):
        """Receive layer.current_edge_color() change event and update view."""
        with qt_signals_blocked(self.border_color_swatch):
            self.border_color_swatch.setColor(
                self.layer.border_color[-1] if self.layer.border_color.size > 0 else self.layer._default_border_color
            )

    def on_change_edge_width_is_relative(self, state: bool):
        """Update edge color of layer model from color picker user input."""
        default_edge_width = self.layer._default_rel_size if state else self.layer._default_border_width
        current_edge_width = self.layer.border_width[-1] if self.layer.border_width.size > 0 else default_edge_width
        if state and current_edge_width > 1:
            current_edge_width = default_edge_width
        # with self.layer.events.border_width.blocker():  # reduces number of UI updates
        self.layer.border_width = current_edge_width
        self.layer.border_width_is_relative = state

    def _on_edge_width_is_relative_change(self, _event):
        """Receive layer.current_edge_color() change event and update view."""
        if self.layer.border_width_is_relative:
            self.border_width_slider.setPageStep(0.05)
            self.border_width_slider.setRange(0, 1)
        else:
            self.border_width_slider.setPageStep(1)
            self.border_width_slider.setRange(0, 100)
        with qt_signals_blocked(self.border_width_relative):
            self.border_width_relative.setChecked(self.layer.border_width_is_relative)

    def _on_editable_or_visible_change(self, event=None):
        """Receive layer model editable change event & enable/disable buttons.

        Parameters
        ----------
        event : napari.utils.event.Event, optional
            The napari event that triggered this method, by default None.
        """
        set_widgets_enabled_with_opacity(
            self,
            [
                self.scaling_checkbox,
                self.text_display_checkbox,
                self.face_color_swatch,
                self.border_color_swatch,
                self.size_slider,
                self.opacity_slider,
                self.blending_combobox,
                self.border_width_slider,
                self.border_width_relative,
                self.symbol_combobox,
            ],
            self.layer.editable and self.layer.visible,
        )
        super()._on_editable_or_visible_change()

    def close(self):
        """Disconnect events when widget is closing."""
        disconnect_events(self.layer.text.events, self)
        super().close()
