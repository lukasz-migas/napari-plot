"""Tests for the grid line controls popup."""

from __future__ import annotations

import typing as ty

import numpy as np
import pytest
from qtpy.QtCore import QCoreApplication, QEvent, Qt
from qtpy.QtWidgets import QWidget

from napari_plot._qt.component_controls.qt_grid_lines_controls import QtGridLinesControls
from napari_plot.components.viewer_model import ViewerModel


def test_grid_lines_controls_update_overlay(qtbot) -> None:
    """The popup edits visibility, color, opacity, width and minor lines."""
    viewer = ViewerModel()
    controls = QtGridLinesControls(viewer)
    qtbot.addWidget(controls)
    overlay = viewer.grid_lines

    assert controls.auto_color_checkbox.isChecked()
    assert not controls.color_swatch.isEnabled()

    controls.visible_checkbox.click()
    assert overlay.visible
    controls.auto_color_checkbox.click()
    assert overlay.color is not None
    assert controls.color_swatch.isEnabled()
    controls.on_change_color(np.asarray([1.0, 0.0, 0.0, 1.0]))
    np.testing.assert_allclose(overlay.color, [1, 0, 0, 1])
    controls.opacity_slider.setValue(0.6)
    controls.on_change_opacity()
    assert overlay.opacity == pytest.approx(0.6)
    controls.width_slider.setValue(2.0)
    controls.on_change_width()
    assert overlay.width == 2.0
    controls.minor_checkbox.click()
    assert overlay.minor

    controls.auto_color_checkbox.click()
    assert overlay.color is None
    assert not controls.color_swatch.isEnabled()


def test_grid_lines_controls_follow_overlay(qtbot) -> None:
    """Changes made elsewhere are reflected in the popup."""
    viewer = ViewerModel()
    controls = QtGridLinesControls(viewer)
    qtbot.addWidget(controls)
    overlay = viewer.grid_lines

    overlay.visible = True
    overlay.opacity = 0.8
    overlay.width = 1.5
    overlay.minor = True
    overlay.color = "blue"
    assert controls.visible_checkbox.isChecked()
    assert controls.opacity_slider.value() == pytest.approx(0.8)
    assert controls.width_slider.value() == pytest.approx(1.5)
    assert controls.minor_checkbox.isChecked()
    assert not controls.auto_color_checkbox.isChecked()
    np.testing.assert_allclose(controls.color_swatch.color, [0, 0, 1, 1])

    overlay.color = None
    viewer.canvas.background_color_override = "white"
    assert controls.auto_color_checkbox.isChecked()
    np.testing.assert_allclose(controls.color_swatch.color, [0, 0, 0, 1])


def _connection_count(emitter: ty.Any) -> int:
    """Return the number of callbacks on a psygnal signal or a napari event emitter."""
    return len(emitter.callbacks) if hasattr(emitter, "callbacks") else len(emitter)


@pytest.mark.parametrize("dismissal", ["qt-close", "escape", "parent"])
def test_grid_lines_controls_disconnect_on_dismissal(qtbot, dismissal: str) -> None:
    """Closing the popup in any way removes its overlay and canvas callbacks."""
    viewer = ViewerModel()
    events = viewer.grid_lines.events
    emitters = (
        events.visible,
        events.color,
        events.opacity,
        events.width,
        events.minor,
        viewer.canvas.events.background_color,
    )
    before = [_connection_count(emitter) for emitter in emitters]
    parent = QWidget()
    controls = QtGridLinesControls(viewer, parent)
    assert [_connection_count(emitter) for emitter in emitters] == [count + 1 for count in before]
    controls.show()
    if dismissal == "qt-close":
        QWidget.close(controls)
    elif dismissal == "escape":
        qtbot.keyClick(controls, Qt.Key.Key_Escape)
    else:
        parent.deleteLater()
    QCoreApplication.sendPostedEvents(parent if dismissal == "parent" else controls, QEvent.Type.DeferredDelete)

    assert [_connection_count(emitter) for emitter in emitters] == before
    second = QtGridLinesControls(viewer)
    try:
        viewer.grid_lines.width = 3.0
        viewer.canvas.background_color_override = "white"
        assert second.width_slider.value() == 3.0
    finally:
        second.close()
        QCoreApplication.sendPostedEvents(second, QEvent.Type.DeferredDelete)
