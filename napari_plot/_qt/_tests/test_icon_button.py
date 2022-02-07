"""Test image buttons."""
import pytest
from napari.layers import Points
from napari.layers.points._points_constants import Mode

from napari_plot._qt.widgets.qt_icon_button import SIZES, QtImagePushButton, QtModePushButton, QtModeRadioButton


@pytest.mark.parametrize("size_name", SIZES)
def test_qt_image_push_button(qtbot, size_name):
    btn = QtImagePushButton()
    qtbot.addWidget(btn)

    btn.set_size_name(size_name)
    assert btn.objectName() == size_name


def test_radio_button(qtbot):
    """Make sure the QtModeRadioButton works to change layer modes"""
    layer = Points()
    assert layer.mode != Mode.ADD

    btn = QtModeRadioButton(layer, "new_points", Mode.ADD, tooltip="tooltip")
    assert btn.toolTip() == "tooltip"
    assert btn.icon() is not None

    btn.click()
    qtbot.wait(50)
    assert layer.mode == "add"


def test_push_button(qtbot):
    """Make sure the QtModePushButton works with callbacks"""
    layer = Points()

    def set_test_prop():
        layer.test_prop = True

    btn = QtModePushButton(layer, "new_points", slot=set_test_prop, tooltip="tooltip")
    assert btn.toolTip() == "tooltip"
    assert btn.icon() is not None

    btn.click()
    qtbot.wait(50)
    assert layer.test_prop
