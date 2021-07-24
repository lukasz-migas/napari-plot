"""Line controls"""
import typing as ty

from napari._qt.utils import disable_with_opacity, qt_signals_blocked
from napari._qt.widgets.qt_color_swatch import QColorSwatch
from qtpy.QtCore import Qt

from napari_1d._qt.helpers import make_label, make_slider

from .qt_layer_controls_base import QtLayerControls

if ty.TYPE_CHECKING:
    from napari_1d.layers import Line


class QtLineControls(QtLayerControls):
    """Line controls"""

    def __init__(self, layer: "Line"):
        super().__init__(layer)
        self.layer.events.color.connect(self._on_color_change)
        self.layer.events.width.connect(self._on_width_change)
        self.layer.events.method.connect(self._on_method_change)
        self.layer.events.editable.connect(self._on_editable_change)

        self.width_slider = make_slider(self, 1, 25, tooltip="Line width.")
        self.width_slider.setFocusPolicy(Qt.NoFocus)
        self.width_slider.setValue(int(self.layer.width))
        self.width_slider.valueChanged.connect(self.on_change_width)

        self.color_swatch = QColorSwatch(
            initial_color=self.layer.color,
            tooltip="Click to set new line color",
        )
        self.color_swatch.color_changed.connect(self.on_change_color)

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
                # "method_combobox",
                "opacity_slider",
                "blending_combobox",
            ],
            not self.layer.editable,
        )
        super()._on_editable_change(event)
