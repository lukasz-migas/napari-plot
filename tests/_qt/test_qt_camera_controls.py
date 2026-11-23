"""Tests for the camera controls popup."""

from qtpy.QtWidgets import QWidget

from napari_plot._qt.component_controls.qt_camera_controls import QtCameraControls, QtCameraWidget
from napari_plot.components.viewer_model import ViewerModel


def _listeners(events) -> set:
    """Return objects whose bound methods are connected to a napari ``EmitterGroup``."""
    return {cb[0]() for emitter in events.emitters.values() for cb in emitter.callbacks if isinstance(cb, tuple)}


def test_camera_popup_disconnects_when_qt_closes_popup(qtbot) -> None:
    """A Qt-driven popup close unsubscribes the inner widget from camera events."""
    viewer = ViewerModel()
    popup = QtCameraControls(viewer)
    popup.show()
    inner = popup.findChild(QtCameraWidget)
    assert inner in _listeners(viewer.camera.events)

    # popups closed by clicking outside go through closeEvent, not the Python ``close`` override
    QWidget.close(popup)
    assert inner not in _listeners(viewer.camera.events)


def test_camera_widget_close_disconnects_camera_events(qtbot) -> None:
    """Closing the docked camera widget unsubscribes it from camera events."""
    viewer = ViewerModel()
    widget = QtCameraWidget(viewer, None)
    qtbot.addWidget(widget)
    assert widget in _listeners(viewer.camera.events)

    widget.close()
    assert widget not in _listeners(viewer.camera.events)


def test_camera_widgets_preserve_model_precision(qtbot) -> None:
    viewer = ViewerModel()
    widget = QtCameraWidget(viewer, None)
    qtbot.addWidget(widget)
    limits = (1 / 3, 2 / 3, 1 / 7, 2 / 7)

    viewer.camera.rect = limits
    viewer.camera.extent = limits

    assert viewer.camera.rect == limits
    assert viewer.camera.extent == limits
    assert widget.x_min.value() == round(limits[0], 6)
    assert widget.extent_x_min.value() == round(limits[0], 6)
