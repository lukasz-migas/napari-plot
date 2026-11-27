"""Per-cell views of the axis and camera controls."""

from __future__ import annotations

import pytest
from qtpy.QtWidgets import QWidget

from napari_plot._qt.component_controls.qt_axis_controls import QtAxisWidget
from napari_plot._qt.component_controls.qt_camera_controls import QtCameraWidget
from napari_plot._qt.component_controls.qt_grid_cell_selector import QtGridCellSelector
from napari_plot.components.viewer_model import ViewerModel


@pytest.fixture
def viewer() -> ViewerModel:
    """Viewer with two layers shown side by side in a grid with independent x-axes."""
    viewer = ViewerModel()
    viewer.add_line([[0, 0], [10, 1]], name="first")
    viewer.add_line([[0, 0], [5, 100]], name="second")
    viewer.canvas.grid.update({"enabled": True, "sharex": False})
    return viewer


@pytest.fixture
def parent(qtbot) -> QWidget:
    widget = QWidget()
    qtbot.addWidget(widget)
    return widget


def _items(selector: QtGridCellSelector) -> list:
    return [selector.combobox.itemData(index) for index in range(selector.combobox.count())]


def test_selector_lists_cells_and_falls_back_to_all_cells(viewer: ViewerModel, parent: QWidget) -> None:
    selector = QtGridCellSelector(viewer, parent)
    targets = []
    selector.target_changed.connect(targets.append)
    assert _items(selector) == [None, (0, 0), (0, 1)]
    assert selector.combobox.itemText(2) == "Cell 1, 2 - second"
    assert not selector.isHidden()

    selector.set_target((0, 1))
    assert selector.target == (0, 1)
    viewer.layers[1].visible = False
    assert selector.target is None
    assert targets == [(0, 1), None]

    viewer.canvas.grid.enabled = False
    assert selector.isHidden()
    viewer.canvas.grid.update({"enabled": True, "joint": True})
    assert not selector.isEnabled()
    selector.disconnect_viewer()


def test_axis_widget_edits_cell_overrides(viewer: ViewerModel, parent: QWidget) -> None:
    """In the view of a cell, edits override the viewer setting in that cell only and can be reset."""
    widget = QtAxisWidget(viewer, parent, target=(0, 1))
    layout = widget._layout
    assert widget.target == (0, 1)
    assert widget.cell_selector.target == (0, 1)
    assert not layout.isRowVisible(widget.x_label_margin_spin)
    assert layout.isRowVisible(widget.x_visible_checkbox.parentWidget())
    assert widget.x_axis_edit.text() == viewer.axis.x_label
    assert widget._reset_buttons["x_label"].isHidden()

    widget.x_axis_edit.setText("Cell x")
    assert viewer.canvas.grid._find_cell(0, 1) is None  # typing alone does not touch the models
    widget.x_axis_edit.editingFinished.emit()
    widget.label_font_size.setValue(15)
    widget.x_visible_checkbox.setChecked(False)
    cell = viewer.canvas.grid._find_cell(0, 1)
    assert (cell.x_label, cell.label_size, cell.x_visible) == ("Cell x", 15, False)
    assert viewer.axis.x_label != "Cell x"
    assert not widget._reset_buttons["x_label"].isHidden()
    assert widget._reset_buttons["y_label"].isHidden()

    # editing the viewer keeps the cell's overrides; the cell view still shows them
    viewer.axis.x_label = "Global x"
    assert cell.x_label == "Cell x"
    assert widget.x_axis_edit.text() == "Cell x"

    widget._reset_buttons["x_label"].click()
    assert cell.x_label is None
    assert widget.x_axis_edit.text() == "Global x"

    widget.x_categories_edit.setText("a, b")
    widget.x_categories_edit.editingFinished.emit()
    assert cell.x_categories == ("a", "b")
    assert widget.x_scale_combobox.currentText() == "categorical"
    widget.x_scale_combobox.setCurrentText("log")
    assert cell.x_categories is None
    assert cell.x_scale == "log"
    assert viewer.axis.x_scale == "linear"

    widget.reset_cell_btn.click()
    assert cell.overrides() == ()

    widget.set_target(None)
    assert layout.isRowVisible(widget.x_label_margin_spin)
    assert not layout.isRowVisible(widget.x_visible_checkbox.parentWidget())
    assert widget.x_axis_edit.text() == "Global x"
    widget.disconnect_viewer()


def test_axis_widget_resets_all_cell_overrides(viewer: ViewerModel, parent: QWidget) -> None:
    viewer.canvas.grid.cell(0, 0).tick_size = 12
    viewer.canvas.grid.cell(0, 1).x_label = "Own"
    widget = QtAxisWidget(viewer, parent)
    assert widget.reset_all_cells_btn.isEnabled()
    widget.tick_font_size.setValue(9)
    assert viewer.axis.tick_size == 9
    assert viewer.canvas.grid.cell(0, 0).tick_size == 12

    widget.reset_all_cells_btn.click()
    assert all(cell.overrides() == () for cell in viewer.canvas.grid.cells)
    assert not widget.reset_all_cells_btn.isEnabled()
    widget.disconnect_viewer()


def test_camera_widget_edits_cell_limits(viewer: ViewerModel, parent: QWidget) -> None:
    """The cell view edits the cell's own limits; the shared y-axis can only be edited for all cells."""
    widget = QtCameraWidget(viewer, parent, target=(0, 1))
    assert not widget._layout.isRowVisible(widget.mouse_pan_checkbox)
    assert widget.extent_x_min.isReadOnly()
    assert widget.x_min.isEnabled()
    assert not widget.y_min.isEnabled()
    assert not widget.y_range_min.isEnabled()

    widget.x_min.setValue(1)
    assert viewer.cell_rect(0, 1)[0] == 1
    viewer.set_cell_rect(0, 1, 2, 3, *viewer.camera.rect[2:])
    assert (widget.x_min.value(), widget.x_max.value()) == (2, 3)

    widget.x_range_min.setText("1")
    widget.x_range_max.setText("4")
    widget.on_change_x_range()
    assert viewer.canvas.grid._find_cell(0, 1).xlim == (1, 4)
    assert viewer.camera.x_range is None

    widget.set_target(None)
    assert widget._layout.isRowVisible(widget.mouse_pan_checkbox)
    assert widget.y_min.isEnabled()
    assert widget.x_range_min.text() == ""
    assert widget.reset_all_cells_btn.isEnabled()
    widget.reset_all_cells_btn.click()
    assert viewer.canvas.grid._find_cell(0, 1).xlim is None

    widget.close()
