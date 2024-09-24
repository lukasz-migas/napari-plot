"""Test controls"""

import numpy as np
import pytest
from napari.utils.colormaps.standardize_color import transform_color

from napari_plot._qt.layer_controls.qt_multiline_controls import QtMultiLineControls
from napari_plot.layers import MultiLine

# Test data
np.random.seed(0)
_MULTILINE = {"x": np.random.random(10), "ys": np.random.random((10, 4))}


@pytest.mark.parametrize("layer", [MultiLine(_MULTILINE)])
def test_multiline_controls_creation(qtbot, layer):
    """Check basic creation of QtMultiLineControls works"""
    qtctrl = QtMultiLineControls(layer)
    qtbot.addWidget(qtctrl)

    assert qtctrl.selection_spin.maximum() == layer.color.shape[0] - 1  # index starts at 0

    # test face color
    target_color = layer.color[0]
    np.testing.assert_almost_equal(transform_color(qtctrl.color_swatch.color)[0], target_color)

    qtctrl.selection_spin.setValue(2)
    target_color = layer.color[2]
    np.testing.assert_almost_equal(transform_color(qtctrl.color_swatch.color)[0], target_color)
