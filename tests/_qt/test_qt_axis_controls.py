"""Tests for the axis controls popup content."""

import pytest
from napari.utils.events import EmitterGroup
from pytestqt.qtbot import QtBot
from qtpy.QtCore import QCoreApplication, QEvent, Qt
from qtpy.QtWidgets import QWidget

from napari_plot._qt.component_controls.qt_axis_controls import QtAxisControls, QtAxisWidget
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


def test_axis_label_applies_when_editing_finished(qtbot) -> None:
    """Labels update the axis once editing finishes, not on every keystroke, and only when they changed."""
    viewer = ViewerModel()
    parent = QWidget()
    qtbot.addWidget(parent)
    controls = QtAxisWidget(viewer, parent)
    events = []
    viewer.axis.events.x_label.connect(events.append)

    controls.x_axis_edit.setText("Time")
    assert viewer.axis.x_label != "Time"
    controls.x_axis_edit.editingFinished.emit()
    assert viewer.axis.x_label == "Time"
    controls.x_axis_edit.editingFinished.emit()
    assert len(events) == 1


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


@pytest.mark.parametrize("dismissal", ["escape", "qt-close", "parent-deletion"])
def test_axis_popup_disconnects_on_dismissal(qtbot: QtBot, dismissal: str) -> None:
    """Dismissing the popup removes its axis and theme listeners immediately upon deletion."""
    viewer = ViewerModel()
    parent = QWidget()
    popup = QtAxisControls(viewer, parent)
    popup.show()
    inner = popup.axis_widget
    assert _has_listener(viewer.axis.events, inner)
    assert _has_listener(viewer.events, inner)

    with qtbot.waitSignal(popup.destroyed):
        if dismissal == "parent-deletion":
            parent.deleteLater()
            QCoreApplication.sendPostedEvents(parent, QEvent.Type.DeferredDelete)
        else:
            qtbot.addWidget(parent)
            if dismissal == "escape":
                qtbot.keyClick(popup, Qt.Key.Key_Escape)
            else:
                QWidget.close(popup)
            QCoreApplication.sendPostedEvents(popup, QEvent.Type.DeferredDelete)

    assert not _has_listener(viewer.axis.events, inner)
    assert not _has_listener(viewer.events, inner)


def test_axis_popup_reopens_with_current_visibility(qtbot: QtBot) -> None:
    """The reopened checkbox starts with the model value and stays in sync."""
    viewer = ViewerModel()
    viewer.axis.visible = True
    parent = QWidget()
    qtbot.addWidget(parent)
    popup = QtAxisControls(viewer, parent)
    popup.show()
    with qtbot.waitSignal(popup.destroyed):
        qtbot.keyClick(popup, Qt.Key.Key_Escape)
        QCoreApplication.sendPostedEvents(popup, QEvent.Type.DeferredDelete)

    reopened = QtAxisControls(viewer, parent)
    reopened.show()
    try:
        assert reopened.axis_widget.visible_checkbox.isChecked()
        reopened.axis_widget.visible_checkbox.setChecked(False)
        assert not viewer.axis.visible
        viewer.axis.visible = True
        assert reopened.axis_widget.visible_checkbox.isChecked()
    finally:
        reopened.close()
        QCoreApplication.sendPostedEvents(reopened, QEvent.Type.DeferredDelete)


def _has_listener(events: EmitterGroup, listener: object) -> bool:
    """Check whether a bound method of the listener is connected to the event group."""
    return any(
        isinstance(callback, tuple) and callback[0]() is listener
        for emitter in events.emitters.values()
        for callback in emitter.callbacks
    )
