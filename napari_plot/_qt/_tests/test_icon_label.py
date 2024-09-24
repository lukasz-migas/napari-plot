"""Test image labels."""

import pytest

from napari_plot._qt.widgets.qt_icon_label import SIZES, QtQtaLabel


@pytest.mark.parametrize("size_name", SIZES)
def test_qt_image_push_button(qtbot, size_name):
    btn = QtQtaLabel()
    assert btn._icon is None
    btn.set_qta("home")
    assert btn._icon is not None
    qtbot.addWidget(btn)

    btn.set_size_name(size_name)
    assert btn.objectName() == size_name
