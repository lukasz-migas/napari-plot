"""Test controls"""

import numpy as np
import pytest
from napari.utils.colormaps.standardize_color import transform_color

from napari_plot._qt.layer_controls.qt_infline_controls import QtInfLineControls
from napari_plot.layers import InfLine
from napari_plot.layers.infline._infline_constants import Mode

# Test data
np.random.seed(0)
_INFLINE = [50, 100, 230]


@pytest.mark.parametrize(
    "layer", [InfLine(_INFLINE, orientation="vertical"), InfLine(_INFLINE, orientation="horizontal")]
)
def test_infline_controls_creation(qtbot, layer):
    """Check basic creation of QtInfLineControls works"""
    qtctrl = QtInfLineControls(layer)
    qtbot.addWidget(qtctrl)

    # test face color
    target_color = layer.color[0]
    np.testing.assert_almost_equal(transform_color(qtctrl.color_swatch.color)[0], target_color)

    # ensure edit is disable if no selection
    assert not qtctrl.move_button.isEnabled()
    layer.selected_data = {0}
    # enabled if single item is selected
    assert qtctrl.move_button.isEnabled()
    # disabled if more than one item is selected
    layer.selected_data = {0, 1}
    assert not qtctrl.move_button.isEnabled()

    # Update current face color
    layer.selected_data = {0}
    layer.current_color = "green"
    target_color = layer.color[0]
    np.testing.assert_almost_equal(transform_color(qtctrl.color_swatch.color)[0], target_color)

    # check change of mode
    layer.mode = Mode.MOVE
    assert layer.mode == str(Mode.MOVE)
    assert layer._mode == Mode.MOVE
    assert qtctrl.move_button.isChecked()

    # check change of mode
    layer.mode = Mode.SELECT
    assert layer.mode == str(Mode.SELECT)
    assert layer._mode == Mode.SELECT
    assert qtctrl.select_button.isChecked()

    layer.mode = "pan_zoom"
    assert layer._mode == Mode.PAN_ZOOM
    assert qtctrl.panzoom_button.isChecked()
