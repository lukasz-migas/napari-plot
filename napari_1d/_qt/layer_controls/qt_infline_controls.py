"""Scatter layer controls"""
import typing as ty

import numpy as np
from napari._qt.utils import disable_with_opacity, qt_signals_blocked
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from napari._qt.widgets.qt_mode_buttons import QtModePushButton, QtModeRadioButton
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QButtonGroup, QHBoxLayout

from ...layers.infline._infline_constants import Mode
from ..helpers import make_label
from .qt_layer_controls_base import QtLayerControls

if ty.TYPE_CHECKING:
    from napari_1d.layers import Scatter


class QtInfLineControls(QtLayerControls):
    """Qt view and controls for the napari-1d Scatter layer.

    Parameters
    ----------
    layer : napari_1d.layers.Scatter
        An instance of a Scatter layer.

    Attributes
    ----------
    layer : napari_1d.layers.Scatter
        An instance of a napari Points layer.
    layout : qtpy.QtWidgets.QFormLayout
        Layout of Qt widget controls for the layer.
    editable_checkbox : qtpy.QtWidgets.QCheckBox
        Checkbox widget to control editability of the layer.
    blending_combobox : qtpy.QtWidgets.QComboBox
        Dropdown widget to select blending mode of layer.
    opacity_slider : qtpy.QtWidgets.QSlider
        Slider controlling opacity of the layer.
    color_swatch : qtpy.QtWidgets.QFrame
        Color swatch showing the color of the region
    move_button : napari._qt.widgets.qt_mode_buttons.QtModeRadioButton
        Button to move infinite line.
    select_button : napari._qt.widgets.qt_mode_buttons.QtModeRadioButton
        Button to select infinite line.
    add_button : napari._qt.widgets.qt_mode_buttons.QtModeRadioButton
        Add new infinite line.
    delete_button : napari._qt.widgets.qt_mode_buttons.QtModeRadioButton
        Button to delete selected infinite line(s).
    """

    def __init__(self, layer: "Scatter"):
        super().__init__(layer)
        self.layer.events.mode.connect(self._on_mode_change)
        self.layer.events.color.connect(self._on_color_change)
        self.layer.events.editable.connect(self._on_editable_change)

        self.color_swatch = QColorSwatchEdit(
            initial_color=self.layer.color,
            tooltip="Click to set face color",
        )
        self.color_swatch.color_changed.connect(self.on_change_color)  # noqa

        self.add_button = QtModeRadioButton(layer, "add_points", Mode.ADD, tooltip="Add infinite line (A)")
        self.select_button = QtModeRadioButton(
            layer, "select_points", Mode.SELECT, tooltip="Select infinite line(s) (S)"
        )
        self.move_button = QtModeRadioButton(layer, "move_region", Mode.MOVE, tooltip="Move infinite line (M)")
        self.panzoom_button = QtModeRadioButton(
            layer,
            "pan_zoom",
            Mode.PAN_ZOOM,
            tooltip="Pan/zoom (Z)",
            checked=True,
        )
        self.delete_button = QtModePushButton(layer, "delete_shape", tooltip="Delete selected infinite lines")

        self.button_group = QButtonGroup(self)
        self.button_group.addButton(self.add_button)
        self.button_group.addButton(self.move_button)
        self.button_group.addButton(self.select_button)
        self.button_group.addButton(self.panzoom_button)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self.add_button)
        button_row.addWidget(self.move_button)
        button_row.addWidget(self.select_button)
        button_row.addWidget(self.panzoom_button)
        button_row.addWidget(self.delete_button)
        button_row.setContentsMargins(0, 0, 0, 5)
        button_row.setSpacing(4)

        # add widgets to the layout
        self.layout.addRow(make_label(self, "Opacity"), self.opacity_slider)
        self.layout.addRow(make_label(self, "Blending"), self.blending_combobox)
        self.layout.addRow(make_label(self, "Color"), self.color_swatch)
        self.layout.addRow(make_label(self, "Editable"), self.editable_checkbox)
        self.layout.addRow(button_row)
        self._on_editable_change()

    def _on_mode_change(self, event):
        """Update ticks in checkbox widgets when points layer mode is changed.

        Available modes for scatter layer are:
        * MOVE
        * PAN_ZOOM

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.

        Raises
        ------
        ValueError
            Raise error if event.mode is not ADD, PAN_ZOOM, or SELECT.
        """
        mode = event.mode
        if mode == Mode.ADD:
            self.add_button.setChecked(True)
        elif mode == Mode.MOVE:
            self.move_button.setChecked(True)
        elif mode == Mode.SELECT:
            self.select_button.setChecked(True)
        elif mode == Mode.PAN_ZOOM:
            self.panzoom_button.setChecked(True)
        else:
            raise ValueError(f"Mode {mode} not recognized")

    @Slot(np.ndarray)  # noqa
    def on_change_color(self, color: np.ndarray):
        """Update face color of layer model from color picker user input."""
        self.layer.color = color

    def _on_color_change(self, _event):
        """Receive layer.current_face_color() change event and update view."""
        with qt_signals_blocked(self.color_swatch):
            self.color_swatch.setColor(self.layer.color)

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
                "opacity_slider",
                "blending_combobox",
                "color_swatch",
                "add_button",
                "move_button",
                "panzoom_button",
                "delete_button",
            ],
            not self.layer.editable,
        )
        super()._on_editable_change(event)
