"""Test controls"""

import numpy as np
import pytest
from napari.utils.colormaps.standardize_color import transform_color

from napari_plot._qt.layer_controls.qt_region_controls import QtRegionControls
from napari_plot.layers import Region
from napari_plot.layers.region._region_constants import Mode

# Test data
np.random.seed(0)
_REGION = [[50, 100], [100, 200]]


@pytest.mark.parametrize(
    "layer",
    [
        Region(_REGION, orientation="vertical"),
        Region(_REGION, orientation="horizontal"),
    ],
)
def test_region_controls_creation(qtbot, layer):
    """Check basic creation of QtInfLineControls works"""
    qtctrl = QtRegionControls(layer)
    qtbot.addWidget(qtctrl)

    # test face color
    target_color = layer.color[0]
    np.testing.assert_almost_equal(
        transform_color(qtctrl.color_swatch.color)[0], target_color
    )

    # ensure edit is disable if no selection
    assert not qtctrl.edit_button.isEnabled()
    layer.selected_data = {0}
    # enabled if single item is selected
    assert qtctrl.edit_button.isEnabled()
    # disabled if more than one item is selected
    layer.selected_data = {0, 1}
    assert not qtctrl.edit_button.isEnabled()

    # Update current face color
    layer.selected_data = {0}
    layer.current_color = "green"
    target_color = layer.color[0]
    np.testing.assert_almost_equal(
        transform_color(qtctrl.color_swatch.color)[0], target_color
    )

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
