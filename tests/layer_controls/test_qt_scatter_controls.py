"""Test controls"""

import numpy as np
import pytest
from napari.utils.colormaps.standardize_color import transform_color

from napari_plot._qt.layer_controls.qt_scatter_controls import QtScatterControls
from napari_plot.layers import Scatter

# Test data
np.random.default_rng(0)
_SCATTER = np.random.random((10, 2))


@pytest.mark.parametrize("layer", [Scatter(_SCATTER, border_width_is_relative=True)])
def test_scatter_controls_creation(qtbot, layer):
    """Check basic creation of QtScatterControls works"""
    qtctrl = QtScatterControls(layer)
    qtbot.addWidget(qtctrl)

    # test face color
    target_color = layer.face_color[0]
    np.testing.assert_almost_equal(transform_color(qtctrl.face_color_swatch.color)[0], target_color)
    layer.face_color = "red"
    target_color = layer.face_color[0]
    np.testing.assert_almost_equal(transform_color(qtctrl.face_color_swatch.color)[0], target_color)

    # test edge color
    target_color = layer.border_color[0]
    np.testing.assert_almost_equal(transform_color(qtctrl.border_color_swatch.color)[0], target_color)
    layer.border_color = "green"
    target_color = layer.border_color[0]
    np.testing.assert_almost_equal(transform_color(qtctrl.border_color_swatch.color)[0], target_color)

    # test width
    assert qtctrl.border_width_slider.maximum() <= 1.0
    assert qtctrl.border_width_slider.value() <= 1.0

    # change to non-relative edge width
    layer.border_width_is_relative = False
    assert qtctrl.border_width_slider.maximum() > 1.0


def test_scatter_controls_edit_modes_and_delete(qtbot) -> None:
    """Scatter exposes add, select, and delete through the layer controls."""
    layer = Scatter([[1, 2], [3, 4]])
    controls = QtScatterControls(layer)
    qtbot.addWidget(controls)

    controls.add_button.click()
    assert layer.mode == "add"
    controls.select_button.click()
    assert layer.mode == "select"
    layer.selected_data = {0}
    controls.delete_button.click()
    np.testing.assert_array_equal(layer.data, [[3, 4]])
    assert not controls.delete_button.isEnabled()
