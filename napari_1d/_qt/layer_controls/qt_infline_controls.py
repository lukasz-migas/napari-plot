"""Line controls"""
import typing as ty

from napari._qt.utils import disable_with_opacity, qt_signals_blocked
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QButtonGroup, QHBoxLayout

from ...layers.infline._infline_constants import Mode
from .. import helpers as hp
from ..widgets.qt_icon_button import QtModePushButton, QtModeRadioButton
from .qt_layer_controls_base import QtLayerControls

if ty.TYPE_CHECKING:
    from ...layers import InfLine


class QtInfLineControls(QtLayerControls):
    """Line controls

    Parameters
    ----------
    layer : napari_1d.layers.InfLine
        An instance of a napari-1d Line layer.

    Attributes
    ----------
    layer : napari_1d.layers.InfLine
        An instance of a napari-1d Line layer.
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

    def __init__(self, layer: "InfLine"):
        super().__init__(layer)
        self.layer.events.mode.connect(self._on_mode_change)
        self.layer.events.current_color.connect(self._on_current_color_change)
        self.layer.events.width.connect(self._on_width_change)
        self.layer.events.editable.connect(self._on_editable_change)

        self.width_slider = hp.make_slider(
            self, 1, 25, value=self.layer.width, tooltip="Line width.", focus_policy=Qt.NoFocus
        )
        self.width_slider.valueChanged.connect(self.on_change_width)

        self.color_swatch = QColorSwatchEdit(
            initial_color=self.layer.color,
            tooltip="Click to set new line color",
        )
        self.color_swatch.color_changed.connect(self.on_change_current_color)
        self._on_current_color_change(None)

        self.add_button = QtModeRadioButton(layer, "add", Mode.ADD, tooltip="Add infinite line (A)")
        self.select_button = QtModeRadioButton(
            layer, "select_points", Mode.SELECT, tooltip="Select infinite line(s) (S)"
        )
        self.move_button = QtModeRadioButton(layer, "move", Mode.MOVE, tooltip="Move infinite line (M)")
        self.panzoom_button = QtModeRadioButton(
            layer,
            "pan_zoom",
            Mode.PAN_ZOOM,
            tooltip="Pan/zoom (Z)",
            checked=True,
        )
        self.delete_button = QtModePushButton(
            layer,
            "delete_shape",
            # slot=self.layer.remove_selected,
            tooltip="Delete selected infinite lines (Backspace)",
        )

        self.button_group = QButtonGroup(self)
        self.button_group.addButton(self.add_button)
        self.button_group.addButton(self.select_button)
        self.button_group.addButton(self.move_button)
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
        self.layout.addRow(hp.make_label(self, "Opacity"), self.opacity_slider)
        self.layout.addRow(hp.make_label(self, "Blending"), self.blending_combobox)
        self.layout.addRow(hp.make_label(self, "Color"), self.color_swatch)
        self.layout.addRow(hp.make_label(self, "Editable"), self.editable_checkbox)
        self.layout.addRow(button_row)
        self._on_editable_change()

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

    def on_change_method(self, value):
        """Change size of points on the layer model.

        Parameters
        ----------
        value : float
            Size of points.
        """
        self.layer.method = self.method_combobox.currentText()

    def _on_method_change(self, event):
        """Receive marker symbol change event and update the dropdown menu.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        with self.layer.events.method.blocker():
            self.method_combobox.setCurrentText(self.layer.method)

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
                "width_slider",
                "color_swatch",
                "opacity_slider",
                "blending_combobox",
            ],
            self.layer.editable,
        )
        super()._on_editable_change(event)
