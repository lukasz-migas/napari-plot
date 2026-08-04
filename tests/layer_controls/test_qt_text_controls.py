"""Tests for Text layer controls."""

import numpy as np
from napari.utils.colormaps.standardize_color import transform_color
from qtpy.QtGui import QGuiApplication
from qtpy.QtWidgets import QComboBox

from napari_plot._qt.layer_controls.qt_layer_controls_container import layer_to_controls
from napari_plot._qt.layer_controls.qt_text_controls import QtTextControls
from napari_plot.layers import Text


def test_text_controls_creation(qtbot) -> None:
    """Text controls initialize from the first label and layer-wide styles."""
    font_face = QGuiApplication.font().family()
    layer = Text(
        [[1, 2], [3, 4]],
        ["first", "second"],
        size=14,
        color=["red", "blue"],
        alignment="left",
        vertical_alignment="top",
        font_face=font_face,
        bold=True,
        italic=True,
        opacity=0.5,
    )
    controls = QtTextControls(layer)
    qtbot.addWidget(controls)

    assert controls.layer is layer
    assert controls.opacity_slider.value() == 50
    assert controls.blending_combobox.currentData() == layer.blending
    assert controls.size_slider.value() == 14
    assert type(controls.font_face_combobox) is QComboBox
    np.testing.assert_array_equal(
        transform_color(controls.color_swatch.color)[0],
        transform_color("red")[0],
    )
    assert controls.font_face_combobox.currentText() == font_face
    assert controls.bold_checkbox.isChecked()
    assert controls.italic_checkbox.isChecked()
    assert controls.alignment_combobox.currentText() == "left"
    assert controls.vertical_alignment_combobox.currentText() == "top"
    assert layer_to_controls[Text] is QtTextControls


def test_text_controls_apply_layer_styles_and_uniform_color(qtbot) -> None:
    """Typography updates the layer while color replaces the per-label array."""
    layer = Text(
        [[1, 2], [3, 4]],
        ["first", "second"],
        size=14,
        color=["red", "blue"],
        alignment="left",
        vertical_alignment="top",
    )
    controls = QtTextControls(layer)
    qtbot.addWidget(controls)

    controls.size_slider.setValue(18)
    controls.on_change_color(transform_color("green")[0])
    controls.alignment_combobox.setCurrentText("center")
    controls.vertical_alignment_combobox.setCurrentText("baseline")
    controls.bold_checkbox.setChecked(True)
    controls.italic_checkbox.setChecked(True)
    font_face = QGuiApplication.font().family()
    controls.on_change_font_face(font_face)

    assert layer.size == 18
    np.testing.assert_array_equal(
        layer.color,
        np.broadcast_to(transform_color("green"), (2, 4)),
    )
    assert layer.alignment == "center"
    assert layer.vertical_alignment == "baseline"
    assert layer.bold is True
    assert layer.italic is True
    assert layer.font_face == font_face


def test_text_controls_follow_model_changes(qtbot) -> None:
    """Programmatic layer style changes are reflected in the controls."""
    layer = Text([[1, 2]], "label")
    controls = QtTextControls(layer)
    qtbot.addWidget(controls)

    layer.size = 22
    layer.color = "yellow"
    layer.alignment = "right"
    layer.vertical_alignment = "bottom"
    layer.bold = True
    layer.italic = True

    assert controls.size_slider.value() == 22
    np.testing.assert_array_equal(
        transform_color(controls.color_swatch.color)[0],
        transform_color("yellow")[0],
    )
    assert controls.alignment_combobox.currentText() == "right"
    assert controls.vertical_alignment_combobox.currentText() == "bottom"
    assert controls.bold_checkbox.isChecked()
    assert controls.italic_checkbox.isChecked()
