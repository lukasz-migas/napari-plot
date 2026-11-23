"""Tests for Qt Centroids controls."""

from napari_plot._qt.layer_controls.qt_centroids_controls import QtCentroidControls
from napari_plot.layers import Centroids


def test_centroids_controls_sync_orientation_and_width(qtbot) -> None:
    """Changes from the GUI and model stay synchronized."""
    layer = Centroids([[2, 3]])
    controls = QtCentroidControls(layer)
    qtbot.addWidget(controls)

    controls.orientation_combobox.setCurrentText("horizontal")
    assert layer.orientation == "horizontal"
    layer.orientation = "vertical"
    assert controls.orientation_combobox.currentText() == "vertical"

    controls.width_slider.setValue(4)
    assert layer.width == 4
    layer.width = 6
    assert controls.width_slider.value() == 6
