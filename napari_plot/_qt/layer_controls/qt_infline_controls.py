"""Line controls"""

import typing as ty

import qtextra.helpers as hp
from napari._qt.utils import qt_signals_blocked, set_widgets_enabled_with_opacity
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from qtpy.QtCore import Qt

from napari_plot._qt.layer_controls.qt_layer_controls_base import QtLayerControls
from napari_plot.layers.infline._infline_constants import Mode

if ty.TYPE_CHECKING:
    from napari_plot.layers import InfLine


class QtInfLineControls(QtLayerControls):
    """Line controls

    Parameters
    ----------
    layer : napari_plot.layers.InfLine
        An instance of a InfLine layer.

    Attributes
    ----------
    layer : napari_plot.layers.InfLine
        An instance of a InfLine layer.
    layout : qtpy.QtWidgets.QFormLayout
        Layout of Qt widget controls for the layer.
    editable_checkbox : qtpy.QtWidgets.QCheckBox
        Checkbox widget to control editability of the layer.
    blending_combobox : qtpy.QtWidgets.QComboBox
        Dropdown widget to select blending mode of layer.
    opacity_slider : qtpy.QtWidgets.QSlider
        Slider controlling opacity of the layer.
    width_slider : qtpy.QtWidgets.QSlider
        Slider controlling width of the layer.
    color_swatch : napari._qt.widgets.qt_color_swatch.QColorSwatch
        Color swatch controlling the line color.
    """

    MODE = Mode
    PAN_ZOOM_ACTION_NAME = "activate_centroids_pan_zoom_mode"
    TRANSFORM_ACTION_NAME = "activate_centroids_transform_mode"

    def __init__(self, layer: "InfLine"):
        super().__init__(layer)
        self.layer.events.mode.connect(self._on_mode_change)
        self.layer.events.current_color.connect(self._on_current_color_change)
        self.layer.events.width.connect(self._on_width_change)
        self.layer.events.editable.connect(self._on_editable_or_visible_change)
        self.layer.events.visible.connect(self._on_editable_or_visible_change)
        self.layer.events.selected.connect(self._on_edit_mode_active)

        self.width_slider = hp.make_slider_with_text(
            self,
            1,
            25,
            value=self.layer.width,
            tooltip="Line width.",
            focus_policy=Qt.FocusPolicy.NoFocus,
        )
        self.width_slider.valueChanged.connect(self.on_change_width)

        self.color_swatch = QColorSwatchEdit(
            initial_color=self.layer.color,
            tooltip="Click to set new line color",
        )
        self.color_swatch.color_changed.connect(self.on_change_current_color)
        self._on_current_color_change(None)

        self.add_button = self._radio_button(
            layer,
            "add",
            Mode.ADD,
            True,
            tooltip="Add infinite line (A)",
            action_name="activate_infline_add_mode",
        )
        self.select_button = self._radio_button(
            layer,
            "select_points",
            Mode.SELECT,
            True,
            tooltip="Select infinite line(s) (S)",
            action_name="activate_infline_select_mode",
        )
        self.move_button = self._radio_button(
            layer,
            "move",
            Mode.MOVE,
            True,
            tooltip="Move infinite line (M)",
            action_name="activate_infline_mode_mode",
        )
        self.delete_button = self._action_button(
            layer,
            "delete_shape",
            slot=layer.remove_selected,
            tooltip="Delete selected infinite lines (Backspace)",
            edit_button=True,
        )

        self.button_grid.addWidget(self.delete_button, 0, 2)
        self.button_grid.addWidget(self.add_button, 0, 3)
        self.button_grid.addWidget(self.select_button, 0, 4)
        self.button_grid.addWidget(self.move_button, 0, 5)

        # add widgets to the layout
        self.layout().addRow(self.button_grid)
        self.layout().addRow(self.opacity_label, self.opacity_slider)
        self.layout().addRow(hp.make_label(self, "Width"), self.width_slider)
        self.layout().addRow(hp.make_label(self, "Blending"), self.blending_combobox)
        self.layout().addRow(hp.make_label(self, "Color"), self.color_swatch)
        self.layout().addRow(hp.make_label(self, "Editable"), self.editable_checkbox)
        self._on_editable_or_visible_change()
        self._on_edit_mode_active()

    def _on_edit_mode_active(self, event=None):
        """Enable/disable `edit` mode when correct number of regions is selected."""
        show = len(self.layer.selected_data) == 1
        set_widgets_enabled_with_opacity(self, [self.move_button], show)
        if not show:
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
        elif mode == Mode.PAN_ZOOM:
            self.panzoom_button.setChecked(True)
        else:
            raise ValueError(f"Mode {mode} not recognized")

    def on_change_width(self, value):
        """Change size of points on the layer model.

        Parameters
        ----------
        value : float
            Size of points.
        """
        self.layer.width = value

    def _on_width_change(self, event=None):
        """Receive layer model size change event and update point size slider.

        Parameters
        ----------
        event : napari.utils.event.Event, optional
            The napari event that triggered this method.
        """
        with self.layer.events.width.blocker():
            value = self.layer.width
            self.width_slider.setValue(int(value))

    def on_change_current_color(self, value):
        """Change size of points on the layer model.

        Parameters
        ----------
        value : float
            Size of points.
        """
        self.layer.current_color = self.color_swatch.color

    def _on_current_color_change(self, event=None):
        """Receive layer.current_face_color() change event and update view."""
        with qt_signals_blocked(self.color_swatch):
            self.color_swatch.setColor(self.layer.current_color)

    # def on_change_method(self, value):
    #     """Change size of points on the layer model.
    #
    #     Parameters
    #     ----------
    #     value : float
    #         Size of points.
    #     """
    #     self.layer.method = self.method_combobox.currentText()
    #
    # def _on_method_change(self, event):
    #     """Receive marker symbol change event and update the dropdown menu.
    #
    #     Parameters
    #     ----------
    #     event : napari.utils.event.Event
    #         The napari event that triggered this method.
    #     """
    #     with self.layer.events.method.blocker():
    #         self.method_combobox.setCurrentText(self.layer.method)

    def _on_editable_or_visible_change(self, event=None):
        """Receive layer model editable change event & enable/disable buttons."""
        set_widgets_enabled_with_opacity(
            self,
            [
                self.width_slider,
                self.color_swatch,
                self.opacity_slider,
                self.blending_combobox,
                self.add_button,
                self.move_button,
                self.select_button,
                self.panzoom_button,
                self.delete_button,
            ],
            self.layer.editable and self.layer.visible,
        )
        super()._on_editable_or_visible_change(event)
