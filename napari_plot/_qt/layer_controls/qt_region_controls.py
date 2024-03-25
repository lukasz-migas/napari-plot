"""Scatter layer controls"""

import typing as ty

import numpy as np
from napari._qt.utils import disable_with_opacity, qt_signals_blocked
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QButtonGroup, QHBoxLayout

import napari_plot._qt.helpers as hp
from napari_plot._qt.layer_controls.qt_layer_controls_base import QtLayerControls
from napari_plot._qt.widgets.qt_icon_button import QtModePushButton, QtModeRadioButton
from napari_plot.layers.region._region_constants import Mode

if ty.TYPE_CHECKING:
    from napari_plot.layers import Region


class QtRegionControls(QtLayerControls):
    """Qt view and controls for the napari Points layer.

    Parameters
    ----------
    layer : napari_plot.layers.Region
        An instance of a Region layer.

    Attributes
    ----------
    layer : napari_plot.layers.Region
        An instance of a Region layer.
    layout : qtpy.QtWidgets.QFormLayout
        Layout of Qt widget controls for the layer.
    editable_checkbox : qtpy.QtWidgets.QCheckBox
        Checkbox widget to control editability of the layer.
    blending_combobox : qtpy.QtWidgets.QComboBox
        Dropdown widget to select blending mode of layer.
    opacity_slider : qtpy.QtWidgets.QSlider
        Slider controlling opacity of the layer.
    edge_color_swatch : qtpy.QtWidgets.QFrame
        Color swatch showing the color of the region
    color_swatch : qtpy.QtWidgets.QFrame
        Color swatch showing the color of the region
    select_button : napari._qt.widgets.qt_mode_buttons.QtModeRadioButton
        Button to select region of interest.
    move_button : napari._qt.widgets.qt_mode_buttons.QtModeRadioButton
        Button to move region of interest.
    panzoom_button : napari._qt.widgets.qt_mode_buttons.QtModeRadioButton
        Button to zoom in and disable other actions.
    """

    def __init__(self, layer: "Region"):
        super().__init__(layer)
        self.layer.events.mode.connect(self._on_mode_change)
        self.layer.events.current_color.connect(self._on_current_color_change)
        self.layer.events.editable.connect(self._on_editable_change)
        self.layer.events.selected.connect(self._on_edit_mode_active)

        self.color_swatch = QColorSwatchEdit(
            initial_color=self.layer.current_color,
            tooltip="Click to set current face color",
        )
        self.color_swatch.color_changed.connect(self.on_change_current_color)  # noqa
        self._on_current_color_change(None)

        self.add_button = QtModeRadioButton(layer, "add", Mode.ADD, tooltip="Add infinite line (A)")
        self.select_button = QtModeRadioButton(layer, "select", Mode.SELECT, tooltip="Select new region (S)")
        self.edit_button = QtModeRadioButton(
            layer,
            "draw",
            Mode.EDIT,
            tooltip="Edit region (E). Please first select ONE region and then modify it's range.",
        )
        self.move_button = QtModeRadioButton(layer, "move", Mode.MOVE, tooltip="Move region (M)")
        self.panzoom_button = QtModeRadioButton(
            layer,
            "pan_zoom",
            Mode.PAN_ZOOM,
            tooltip="Pan/zoom (Z)",
            checked=True,
        )
        self.move_front_button = QtModePushButton(
            layer, "move_front", slot=self.layer.move_to_front, tooltip="Move to front"
        )

        self.move_back_button = QtModePushButton(
            layer,
            "move_back",
            slot=self.layer.move_to_back,
            tooltip="Move to back",
        )
        self.delete_button = QtModePushButton(
            layer, "delete_shape", slot=self.layer.remove_selected, tooltip="Delete selected infinite lines"
        )

        self.button_group = QButtonGroup(self)
        self.button_group.addButton(self.add_button)
        self.button_group.addButton(self.select_button)
        self.button_group.addButton(self.move_button)
        self.button_group.addButton(self.panzoom_button)

        button_row_1 = QHBoxLayout()
        button_row_1.addStretch(1)
        button_row_1.addWidget(self.add_button)
        button_row_1.addWidget(self.select_button)
        button_row_1.addWidget(self.edit_button)
        button_row_1.addWidget(self.move_button)
        button_row_1.addWidget(self.panzoom_button)
        button_row_1.addWidget(self.delete_button)
        button_row_1.setContentsMargins(0, 0, 0, 5)
        button_row_1.setSpacing(4)

        button_row_2 = QHBoxLayout()
        button_row_2.addStretch(1)
        button_row_2.addWidget(self.move_back_button)
        button_row_2.addWidget(self.move_front_button)
        button_row_2.setContentsMargins(0, 0, 0, 5)
        button_row_2.setSpacing(4)

        # add widgets to the layout
        self.layout.addRow(hp.make_label(self, "Opacity"), self.opacity_slider)
        self.layout.addRow(hp.make_label(self, "Blending"), self.blending_combobox)
        self.layout.addRow(hp.make_label(self, "Color"), self.color_swatch)
        self.layout.addRow(hp.make_label(self, "Editable"), self.editable_checkbox)
        self.layout.addRow(button_row_1)
        self.layout.addRow(button_row_2)
        self._on_editable_change()
        self._on_edit_mode_active()

    def _on_edit_mode_active(self, event=None):
        """Enable/disable `edit` mode when correct number of regions is selected."""
        show = len(self.layer.selected_data) == 1
        disable_with_opacity(self, ["edit_button"], show)
        if not show:
            self.edit_button.setChecked(False)

    def _on_mode_change(self, event):
        """Update ticks in checkbox widgets when points layer mode is changed.

        Available modes for points layer are:
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
        if mode == Mode.MOVE:
            self.move_button.setChecked(True)
        elif mode == Mode.ADD:
            self.add_button.setChecked(True)
        elif mode == Mode.SELECT:
            self.select_button.setChecked(True)
        elif mode == Mode.EDIT:
            self.edit_button.setChecked(True)
        elif mode == Mode.PAN_ZOOM:
            self.panzoom_button.setChecked(True)
        else:
            raise ValueError(f"Mode {mode} not recognized")

    @Slot(np.ndarray)  # noqa
    def on_change_current_color(self, color: np.ndarray):
        """Update face color of layer model from color picker user input."""
        self.layer.current_color = color

    def _on_current_color_change(self, _event):
        """Receive layer.current_color() change event and update view."""
        with qt_signals_blocked(self.color_swatch):
            self.color_swatch.setColor(self.layer.current_color)

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
                "move_button",
                "select_button",
                "delete_button",
                "panzoom_button",
                "add_button",
                # "edit_button",
            ],
            self.layer.editable and self.layer.visible,
        )
        super()._on_editable_change(event)
