"""Line controls"""

import typing as ty

import qtextra.helpers as hp
from napari._qt.utils import qt_signals_blocked, set_widgets_enabled_with_opacity
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from qtpy.QtCore import Qt

from napari_plot._qt.layer_controls.qt_layer_controls_base import QtLayerControls

if ty.TYPE_CHECKING:
    from napari_plot.layers import Line


class QtLineControls(QtLayerControls):
    """Line controls

    Parameters
    ----------
    layer : napari_plot.layers.Line
        An instance of a Line layer.

    Attributes
    ----------
    layer : napari_plot.layers.Line
        An instance of a napari-plot Line layer.
    layout : qtpy.QtWidgets.QFormLayout
        Layout of Qt widget controls for the layer.
    blending_combobox : qtpy.QtWidgets.QComboBox
        Dropdown widget to select blending mode of layer.
    opacity_slider : qtpy.QtWidgets.QSlider
        Slider controlling opacity of the layer.
    width_slider : qtpy.QtWidgets.QSlider
        Slider controlling width of the layer.
    color_swatch : napari._qt.widgets.qt_color_swatch.QColorSwatch
        Color swatch controlling the line color.
    """

    PAN_ZOOM_ACTION_NAME = "activate_line_pan_zoom_mode"
    TRANSFORM_ACTION_NAME = "activate_line_transform_mode"

    def __init__(self, layer: "Line"):
        super().__init__(layer)
        self.layer.events.color.connect(self._on_color_change)
        self.layer.events.width.connect(self._on_width_change)
        self.layer.events.method.connect(self._on_method_change)
        self.layer.events.visible.connect(self._on_editable_or_visible_change)

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
        self.color_swatch.color_changed.connect(self.on_change_color)

        # add widgets to layout
        self.layout().addRow(self.button_grid)
        self.layout().addRow(self.opacity_label, self.opacity_slider)
        self.layout().addRow(hp.make_label(self, "Blending"), self.blending_combobox)
        self.layout().addRow(hp.make_label(self, "Line width"), self.width_slider)
        self.layout().addRow(hp.make_label(self, "Line color"), self.color_swatch)
        self._on_editable_or_visible_change()

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
                self.width_slider,
                self.color_swatch,
                self.opacity_slider,
                self.blending_combobox,
            ],
            self.layer.visible,
        )
