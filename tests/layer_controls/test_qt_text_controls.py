"""Tests for Text layer controls."""

import numpy as np
from napari.utils.colormaps.standardize_color import transform_color
from qtpy.QtGui import QFont

from napari_plot._qt.layer_controls.qt_layer_controls_container import layer_to_controls
from napari_plot._qt.layer_controls.qt_text_controls import QtTextControls
from napari_plot.layers import Text


def test_text_controls_creation(qtbot) -> None:
    """Text controls initialize from the first label and layer-wide styles."""
    layer = Text(
        [[1, 2], [3, 4]],
        ["first", "second"],
        size=[14, 24],
        color=["red", "blue"],
        alignment=["left", "right"],
        vertical_alignment=["top", "bottom"],
        font_face="Arial",
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
    np.testing.assert_array_equal(
        transform_color(controls.color_swatch.color)[0],
        transform_color("red")[0],
    )
    assert controls.font_face_combobox.currentFont().family() == "Arial"
    assert controls.bold_checkbox.isChecked()
    assert controls.italic_checkbox.isChecked()
    assert controls.scaling_checkbox.isChecked()
    assert controls.alignment_combobox.currentText() == "left"
    assert controls.vertical_alignment_combobox.currentText() == "top"
    assert layer_to_controls[Text] is QtTextControls


def test_text_controls_apply_values_to_all_labels(qtbot) -> None:
    """Editing a per-label control intentionally replaces the whole array."""
    layer = Text(
        [[1, 2], [3, 4]],
        ["first", "second"],
        size=[14, 24],
        color=["red", "blue"],
        alignment=["left", "right"],
        vertical_alignment=["top", "bottom"],
    )
    controls = QtTextControls(layer)
    qtbot.addWidget(controls)

    controls.size_slider.setValue(18)
    controls.on_change_color(transform_color("green")[0])
    controls.alignment_combobox.setCurrentText("center")
    controls.vertical_alignment_combobox.setCurrentText("baseline")
    controls.bold_checkbox.setChecked(True)
    controls.italic_checkbox.setChecked(True)
    controls.scaling_checkbox.setChecked(False)
    controls.on_change_font_face(QFont("Arial"))

    np.testing.assert_array_equal(layer.size, [18, 18])
    np.testing.assert_array_equal(
        layer.color,
        np.broadcast_to(transform_color("green"), (2, 4)),
    )
    np.testing.assert_array_equal(layer.alignment, ["center", "center"])
    np.testing.assert_array_equal(layer.vertical_alignment, ["baseline", "baseline"])
    assert layer.bold is True
    assert layer.italic is True
    assert layer.scaling is False
    assert layer.font_face == "Arial"


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
    layer.scaling = False

    assert controls.size_slider.value() == 22
    np.testing.assert_array_equal(
        transform_color(controls.color_swatch.color)[0],
        transform_color("yellow")[0],
    )
    assert controls.alignment_combobox.currentText() == "right"
    assert controls.vertical_alignment_combobox.currentText() == "bottom"
    assert controls.bold_checkbox.isChecked()
    assert controls.italic_checkbox.isChecked()
    assert not controls.scaling_checkbox.isChecked()
