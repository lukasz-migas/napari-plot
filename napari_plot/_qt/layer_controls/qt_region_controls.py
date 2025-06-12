"""Scatter layer controls"""

import typing as ty

import numpy as np
import qtextra.helpers as hp
from napari._qt.utils import qt_signals_blocked, set_widgets_enabled_with_opacity
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from qtpy.QtCore import Slot

from napari_plot._qt.layer_controls.qt_layer_controls_base import QtLayerControls
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

    MODE = Mode
    PAN_ZOOM_ACTION_NAME = "activate_region_pan_zoom_mode"
    TRANSFORM_ACTION_NAME = "activate_region_transform_mode"

    def __init__(self, layer: "Region"):
        super().__init__(layer)
        self.layer.events.mode.connect(self._on_mode_change)
        self.layer.events.current_color.connect(self._on_current_color_change)
        self.layer.events.selected.connect(self._on_edit_mode_active)
        self.layer.events.visible.connect(self._on_editable_or_visible_change)

        self.color_swatch = QColorSwatchEdit(
            initial_color=self.layer.current_color,
            tooltip="Click to set current face color",
        )
        self.color_swatch.color_changed.connect(self.on_change_current_color)
        self._on_current_color_change(None)

        self.delete_button = self._action_button(
            layer,
            "delete_shape",
            slot=layer.remove_selected,
            tooltip="Delete selected infinite lines (Backspace)",
            edit_button=True,
        )
        self.add_button = self._radio_button(
            layer,
            "add",
            Mode.ADD,
            True,
            tooltip="Add Region line (A)",
            action_name="activate_region_add_mode",
        )
        self.select_button = self._radio_button(
            layer,
            "select_points",
            Mode.SELECT,
            True,
            tooltip="Select Region line(s) (S)",
            action_name="activate_region_select_mode",
        )
        self.move_button = self._radio_button(
            layer,
            "move",
            Mode.MOVE,
            True,
            tooltip="Move Region line (M)",
            action_name="activate_region_move_mode",
        )
        self.edit_button = self._radio_button(
            layer,
            "draw",
            Mode.EDIT,
            True,
            tooltip="Edit region (E). Please first select ONE region and then modify it's range.",
            action_name="activate_region_edit_mode",
        )

        self.move_front_button = self._action_button(
            layer,
            "move_front",
            slot=layer.move_to_front,
            tooltip="Move to front",
            edit_button=True,
        )
        self.move_back_button = self._action_button(
            layer,
            "move_back",
            slot=layer.move_to_back,
            tooltip="Move to back",
            edit_button=True,
        )
        self.delete_button = self._action_button(
            layer,
            "delete_shape",
            slot=layer.remove_selected,
            tooltip="Delete selected infinite lines (Backspace)",
            edit_button=True,
        )
        self.transform_button.hide()

        self.button_grid.addWidget(self.delete_button, 0, 1)
        self.button_grid.addWidget(self.add_button, 0, 2)
        self.button_grid.addWidget(self.edit_button, 0, 3)
        self.button_grid.addWidget(self.move_button, 0, 4)
        self.button_grid.addWidget(self.select_button, 0, 5)
        # row 2
        self.button_grid.addWidget(self.move_back_button, 1, 1)
        self.button_grid.addWidget(self.move_front_button, 1, 2)

        # add widgets to the layout
        self.layout().addRow(self.button_grid)
        self.layout().addRow(self.opacity_label, self.opacity_slider)
        self.layout().addRow(hp.make_label(self, "Blending"), self.blending_combobox)
        self.layout().addRow(hp.make_label(self, "Color"), self.color_swatch)
        self._on_editable_or_visible_change()
        self._on_edit_mode_active()

    def _on_edit_mode_active(self, event=None):
        """Enable/disable `edit` mode when correct number of regions is selected."""
        show = len(self.layer.selected_data) == 1
        set_widgets_enabled_with_opacity(self, [self.edit_button, self.move_button], show)
        if not show:
            self.edit_button.setChecked(False)
            self.move_button.setChecked(False)

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

    @Slot(np.ndarray)
    def on_change_current_color(self, color: np.ndarray):
        """Update face color of layer model from color picker user input."""
        self.layer.current_color = color

    def _on_current_color_change(self, _event):
        """Receive layer.current_color() change event and update view."""
        with qt_signals_blocked(self.color_swatch):
            self.color_swatch.setColor(self.layer.current_color)

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
                self.opacity_slider,
                self.blending_combobox,
                self.color_swatch,
                self.move_button,
                self.select_button,
                self.delete_button,
                self.panzoom_button,
                self.add_button,
                self.move_back_button,
                self.move_front_button,
            ],
            self.layer.visible,
        )
