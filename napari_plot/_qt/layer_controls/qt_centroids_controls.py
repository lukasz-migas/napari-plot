"""Centroids controls"""

import typing as ty

import qtextra.helpers as hp
from napari._qt.utils import qt_signals_blocked, set_widgets_enabled_with_opacity
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from qtpy.QtCore import Qt

from napari_plot._qt.layer_controls.qt_layer_controls_base import QtLayerControls
from napari_plot.layers.centroids._centroids_constants import COLORING_TRANSLATIONS

if ty.TYPE_CHECKING:
    from napari_plot.layers import Centroids


class QtCentroidControls(QtLayerControls):
    """Line controls

    Parameters
    ----------
    layer : napari_plot.layers.Centroids
        An instance of a Line layer.

    Attributes
    ----------
    layer : napari_plot.layers.Centroids
        An instance of a napari-plot Line layer.
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

    PAN_ZOOM_ACTION_NAME = "activate_centroids_pan_zoom_mode"
    TRANSFORM_ACTION_NAME = "activate_centroids_transform_mode"

    def __init__(self, layer: "Centroids"):
        super().__init__(layer)
        self.layer.events.color.connect(self._on_color_change)
        self.layer.events.width.connect(self._on_width_change)
        self.layer.events.method.connect(self._on_method_change)
        self.layer.events.editable.connect(self._on_editable_or_visible_change)
        self.layer.events.visible.connect(self._on_editable_or_visible_change)

        self.selection_text = hp.make_label(self, "Index")
        self.selection_spin = hp.make_int_spin_box(self, value=0, tooltip="Specify current index.")
        self.selection_spin.valueChanged.connect(self._on_color_change)

        self.width_slider = hp.make_slider_with_text(
            self,
            1,
            25,
            value=self.layer.width,
            tooltip="Line width.",
            focus_policy=Qt.FocusPolicy.NoFocus,
        )
        self.width_slider.valueChanged.connect(self.on_change_width)

        self.coloring_choice = hp.make_combobox(
            self, COLORING_TRANSLATIONS, tooltip="Which centroids should be colored."
        )
        self.coloring_choice.currentTextChanged.connect(self._on_coloring_change)

        self.color_swatch = QColorSwatchEdit(
            initial_color=self.layer.color,
            tooltip="Click to set new line color",
        )
        self.color_swatch.color_changed.connect(self.on_change_color)

        # add widgets to layout
        self.layout().addRow(self.button_grid)
        self.layout().addRow(self.opacity_label, self.opacity_slider)
        self.layout().addRow(hp.make_label(self, "Blending"), self.blending_combobox)
        self.layout().addRow(hp.make_label(self, "Width"), self.width_slider)
        self.layout().addRow(hp.make_label(self, "Color choice"), self.coloring_choice)
        self.layout().addRow(self.selection_text, self.selection_spin)
        self.layout().addRow(hp.make_label(self, "Color"), self.color_swatch)
        self.layout().addRow(hp.make_label(self, "Editable"), self.editable_checkbox)
        self._on_editable_or_visible_change()
        self._on_data_change()
        self._on_color_change()

    def _on_data_change(self, event=None):
        n_lines = len(self.layer.data) - 1
        self.selection_spin.setRange(0, n_lines)

    def _on_coloring_change(self, event=None):
        show_single = self.coloring_choice.currentText() == "single"
        self.selection_text.setVisible(show_single)
        self.selection_spin.setVisible(show_single)

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
        index = self.selection_spin.value()
        current = self.coloring_choice.currentText()
        if current == "single":
            self.layer.update_color(index, self.color_swatch.color)
        elif current == "all":
            self.layer.color = self.color_swatch.color

    def _on_color_change(self, event=None):
        """Receive layer.current_face_color() change event and update view."""
        with qt_signals_blocked(self.color_swatch):
            index = self.selection_spin.value()
            self.color_swatch.setColor(self.layer.color[index])

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
                self.selection_spin,
                self.coloring_choice,
            ],
            self.layer.editable and self.layer.visible,
        )
        super()._on_editable_or_visible_change(event)
