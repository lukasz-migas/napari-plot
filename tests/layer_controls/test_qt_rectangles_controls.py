"""Qt controls for Rectangles."""

import numpy as np
from pytestqt.qtbot import QtBot

from napari_plot._qt.layer_controls.qt_layer_controls_container import layer_to_controls
from napari_plot._qt.layer_controls.qt_rectangles_controls import QtRectanglesControls
from napari_plot.layers import Rectangles


def test_rectangles_controls_sync_independently(qtbot: QtBot) -> None:
    layer = Rectangles([[1, 2]], 3, 4, text=["Peak"])
    controls = layer_to_controls[Rectangles](layer)
    assert isinstance(controls, QtRectanglesControls)
    qtbot.addWidget(controls)

    controls.markers_checkbox.setChecked(True)
    controls.outlines_checkbox.setChecked(False)
    assert layer.show_markers
    assert not layer.show_rectangles
    assert layer.show_text
    controls.text_checkbox.setChecked(False)
    assert not layer.show_text
    assert layer.show_markers

    controls.width_spinbox.setValue(3.5)
    assert layer.outline_width == 3.5
    controls.width_spinbox.stepUp()
    assert layer.outline_width == 4
    controls.width_spinbox.stepDown()
    assert layer.outline_width == 3.5
    layer.outline_width = 4.25
    layer.show_markers = False
    layer.show_rectangles = True
    layer.show_text = True
    assert controls.width_spinbox.value() == 4.25
    assert not controls.markers_checkbox.isChecked()
    assert controls.outlines_checkbox.isChecked()
    assert controls.text_checkbox.isChecked()


def test_rectangles_marker_and_font_style_controls(qtbot: QtBot) -> None:
    layer = Rectangles([[1, 2], [3, 4]], 3, 4, marker_size=[5, 8], marker_symbol=["disc", "diamond"])
    controls = QtRectanglesControls(layer)
    qtbot.addWidget(controls)

    assert controls.marker_size_spinbox.text() == "Per marker"
    assert controls.marker_symbol_combobox.currentIndex() == -1
    assert controls.text_size_spinbox.text() == "Application default"
    np.testing.assert_array_equal(layer.marker_size, [5, 8])
    np.testing.assert_array_equal(layer.marker_symbol, ["disc", "diamond"])
    assert layer.text_size is None

    controls.marker_size_spinbox.setValue(9.5)
    controls.marker_symbol_combobox.setCurrentIndex(controls.marker_symbol_combobox.findData("triangle_up"))
    controls.text_size_spinbox.setValue(14.5)
    assert layer.marker_size == 9.5
    assert layer.marker_symbol == "triangle_up"
    assert layer.text_size == 14.5

    controls.marker_size_spinbox.setValue(0)
    assert controls.marker_size_spinbox.value() == 9.5
    controls.text_size_spinbox.setValue(0)
    assert layer.text_size is None

    layer.marker_size = 7
    layer.marker_symbol = "square"
    layer.text_size = 12
    assert controls.marker_size_spinbox.value() == 7
    assert controls.marker_symbol_combobox.currentData() == "square"
    assert controls.text_size_spinbox.value() == 12

    layer.marker_size = [1, 2]
    layer.marker_symbol = ["disc", "square"]
    assert controls.marker_size_spinbox.text() == "Per marker"
    assert controls.marker_symbol_combobox.currentIndex() == -1
