"""Line controls"""
import typing as ty

from napari._qt.utils import disable_with_opacity, qt_signals_blocked
from napari._qt.widgets.qt_color_swatch import QColorSwatch
from qtpy.QtCore import Qt

from ..helpers import make_label, make_slider
from .qt_layer_controls_base import QtLayerControls

if ty.TYPE_CHECKING:
    from napari_1d.layers import Line


class QtLineControls(QtLayerControls):
    """Line controls

    Parameters
    ----------
    layer : napari_1d.layers.Line
        An instance of a napari-1d Line layer.

    Attributes
    ----------
    layer : napari_1d.layers.Line
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

    def __init__(self, layer: "Line"):
        super().__init__(layer)
        self.layer.events.color.connect(self._on_color_change)
        self.layer.events.width.connect(self._on_width_change)
        self.layer.events.method.connect(self._on_method_change)
        self.layer.events.editable.connect(self._on_editable_change)

        self.width_slider = make_slider(
            self, 1, 25, val=self.layer.width, tooltip="Line width.", focus_policy=Qt.NoFocus
        )
        self.width_slider.valueChanged.connect(self.on_change_width)

        self.color_swatch = QColorSwatch(
            initial_color=self.layer.color,
            tooltip="Click to set new line color",
        )
        self.color_swatch.color_changed.connect(self.on_change_color)

        # add widgets to layout
        self.layout.addRow(make_label(self, "Opacity"), self.opacity_slider)
        self.layout.addRow(make_label(self, "Blending"), self.blending_combobox)
        self.layout.addRow(make_label(self, "Line width"), self.width_slider)
        self.layout.addRow(make_label(self, "Line color"), self.color_swatch)
        self.layout.addRow(make_label(self, "Editable"), self.editable_checkbox)
        self._on_editable_change()

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

    def on_change_color(self, value):
        """Change size of points on the layer model.

        Parameters
        ----------
        value : float
            Size of points.
        """
        self.layer.color = self.color_swatch.color

    def _on_color_change(self, event=None):
        """Receive layer.current_face_color() change event and update view."""
        with qt_signals_blocked(self.color_swatch):
            self.color_swatch.setColor(self.layer.color)

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
            not self.layer.editable,
        )
        super()._on_editable_change(event)
