"""Tests for Bar layer controls."""

from napari_plot._qt.layer_controls.qt_bar_controls import QtBarControls
from napari_plot._qt.layer_controls.qt_layer_controls_container import layer_to_controls
from napari_plot.layers import Bar


def test_bar_controls_update_layer(qtbot) -> None:
    """Bar controls edit geometry and orientation properties."""
    layer = Bar([1, 2])
    controls = QtBarControls(layer)
    qtbot.addWidget(controls)

    controls.orientation_combobox.setCurrentText("horizontal")
    controls.baseline_spinbox.setValue(2)
    controls.width_spinbox.setValue(1.5)
    controls.border_width_spinbox.setValue(3)

    assert layer.orientation == "horizontal"
    assert layer.baseline == 2
    assert layer.width == 1.5
    assert layer.border_width == 3
    assert layer_to_controls[Bar] is QtBarControls
