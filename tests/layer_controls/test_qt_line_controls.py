"""Test controls"""

import numpy as np
import pytest
from napari.utils.colormaps.standardize_color import transform_color

from napari_plot._qt.layer_controls.qt_line_controls import QtLineControls
from napari_plot.layers import Line

# Test data
np.random.seed(0)
_LINE = np.random.random((10, 2))


@pytest.mark.parametrize("layer", [Line(_LINE)])
def test_line_controls_creation(qtbot, layer):
    """Check basic creation of QtLineControls works"""
    qtctrl = QtLineControls(layer)
    qtbot.addWidget(qtctrl)

    # test face color
    target_color = layer.color
    np.testing.assert_almost_equal(transform_color(qtctrl.color_swatch.color)[0], target_color)

    # Update current face color
    layer.color = "red"
    target_color = layer.color
    np.testing.assert_almost_equal(transform_color(qtctrl.color_swatch.color)[0], target_color)
