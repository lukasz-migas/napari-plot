"""Tests for the axis controls popup content."""

from qtpy.QtWidgets import QWidget

from napari_plot._qt.component_controls.qt_axis_controls import QtAxisWidget
from napari_plot.components.axis import AxisScale
from napari_plot.components.viewer_model import ViewerModel


def test_axis_controls_update_scale_and_categories(qtbot) -> None:
    """Scale selectors and category editors update the axis model."""
    viewer = ViewerModel()
    parent = QWidget()
    qtbot.addWidget(parent)
    controls = QtAxisWidget(viewer, parent)
    qtbot.addWidget(controls)

    controls.x_scale_combobox.setCurrentText("log")
    assert viewer.axis.x_scale is AxisScale.LOG

    controls.x_categories_edit.setText("first, second, third")
    controls.x_categories_edit.editingFinished.emit()
    assert viewer.axis.x_categories == ("first", "second", "third")
    assert viewer.axis.x_scale is AxisScale.CATEGORICAL
    assert controls.x_scale_combobox.currentText() == "categorical"

    controls.x_scale_combobox.setCurrentText("linear")
    assert viewer.axis.x_scale is AxisScale.LINEAR
    assert viewer.axis.x_categories is None
    assert controls.x_categories_edit.text() == ""


def test_axis_controls_follow_model_changes(qtbot) -> None:
    """Programmatic scale and category changes update the controls."""
    viewer = ViewerModel()
    parent = QWidget()
    qtbot.addWidget(parent)
    controls = QtAxisWidget(viewer, parent)
    qtbot.addWidget(controls)

    viewer.axis.y_scale = AxisScale.LOG
    assert controls.y_scale_combobox.currentText() == "log"

    viewer.axis.y_categories = ("low", "high")
    assert controls.y_scale_combobox.currentText() == "categorical"
    assert controls.y_categories_edit.text() == "low, high"


def test_axis_popup_disconnects_when_qt_closes_popup(qtbot) -> None:
    """A Qt-driven popup close unsubscribes the inner widget from axis events."""
    from napari_plot._qt.component_controls.qt_axis_controls import QtAxisControls

    viewer = ViewerModel()
    popup = QtAxisControls(viewer)
    popup.show()
    inner = popup.findChild(QtAxisWidget)
    assert inner in _listeners(viewer.axis.events)

    # popups closed by clicking outside go through closeEvent, not the Python ``close`` override
    QWidget.close(popup)
    assert inner not in _listeners(viewer.axis.events)


def _listeners(events) -> set:
    """Return objects whose bound methods are connected to a napari ``EmitterGroup``."""
    return {cb[0]() for emitter in events.emitters.values() for cb in emitter.callbacks if isinstance(cb, tuple)}
