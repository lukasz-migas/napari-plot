"""Tests for Bar layer controls."""

import numpy as np

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


def test_bar_controls_delete_selected(qtbot) -> None:
    """The delete button removes selected rows and follows selection state."""
    layer = Bar([1, 2, 3])
    controls = QtBarControls(layer)
    qtbot.addWidget(controls)

    assert not controls.delete_button.isEnabled()
    layer.selected_data = {1}
    assert controls.delete_button.isEnabled()
    controls.delete_button.click()
    np.testing.assert_array_equal(layer.values, [1, 3])
    assert not controls.delete_button.isEnabled()
