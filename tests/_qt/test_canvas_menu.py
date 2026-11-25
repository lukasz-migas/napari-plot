"""Canvas right-click menu."""

from __future__ import annotations

import typing as ty

import pytest
from qtpy.QtCore import QPoint, Qt
from qtpy.QtWidgets import QAction, QMenu

from napari_plot.components.dragtool import DragMode

if ty.TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


@pytest.fixture
def opened_menus(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, QAction]]:
    """Record the actions of every canvas menu instead of showing it."""
    from napari_plot._qt import qt_canvas_menu

    menus: list[dict[str, QAction]] = []

    class RecordingMenu(QMenu):
        def exec(self, *_args: ty.Any) -> None:
            actions: dict[str, QAction] = {}
            for action in self.actions():
                actions[action.objectName()] = action
                if submenu := action.menu():
                    actions.update({sub.objectName(): sub for sub in submenu.actions()})
            menus.append(actions)

    monkeypatch.setattr(qt_canvas_menu, "QMenu", RecordingMenu)
    return menus


def _canvas(viewer: ty.Any) -> ty.Any:
    return viewer.window._qt_viewer.canvas


def _right_click(qtbot: QtBot, viewer: ty.Any, move: int = 0) -> None:
    widget = _canvas(viewer).native
    center = QPoint(widget.width() // 2, widget.height() // 2)
    qtbot.mousePress(widget, Qt.MouseButton.RightButton, pos=center)
    if move:
        end = center + QPoint(move, move)
        qtbot.mouseMove(widget, pos=center + QPoint(move // 2, move // 2))
        qtbot.mouseMove(widget, pos=end)
        qtbot.wait(20)  # the canvas throttles mouse moves
        qtbot.mouseRelease(widget, Qt.MouseButton.RightButton, pos=end)
    else:
        qtbot.mouseRelease(widget, Qt.MouseButton.RightButton, pos=center)


def test_right_click_opens_menu_and_toggles(
    make_napari_plot_viewer: ty.Callable, qtbot: QtBot, opened_menus: list[dict[str, QAction]]
) -> None:
    """A right click opens the menu; its commands change tools and overlays."""
    viewer = make_napari_plot_viewer(show=True)
    viewer.add_line([[0, 0], [1, 1]])
    _right_click(qtbot, viewer)

    assert len(opened_menus) == 1
    actions = opened_menus[0]
    assert {
        "napari_plot.canvas.crosshair",
        "napari_plot.canvas.hover",
        "napari_plot.canvas.grid_lines",
        "napari_plot.canvas.clipboard",
        "napari_plot.canvas.export_figure",
        "napari_plot.canvas.tool.lasso",
    } <= set(actions)
    assert actions["napari_plot.canvas.tool.auto"].isChecked()
    assert not actions["napari_plot.canvas.crosshair"].isChecked()

    actions["napari_plot.canvas.crosshair"].trigger()
    actions["napari_plot.canvas.tool.lasso"].trigger()
    assert viewer.crosshair.visible
    assert viewer.drag_tool.active == DragMode.LASSO


def test_right_drag_pans_without_menu(
    make_napari_plot_viewer: ty.Callable, qtbot: QtBot, opened_menus: list[dict[str, QAction]]
) -> None:
    """A right-drag keeps panning the plot and does not open the menu."""
    viewer = make_napari_plot_viewer(show=True)
    viewer.add_line([[0, 0], [1, 1]])
    _right_click(qtbot, viewer, move=40)
    assert opened_menus == []


def test_right_click_cancels_selection_without_menu(
    make_napari_plot_viewer: ty.Callable, qtbot: QtBot, opened_menus: list[dict[str, QAction]]
) -> None:
    """While a polygon is being drawn, a right click cancels it instead of opening the menu."""
    viewer = make_napari_plot_viewer(show=True)
    viewer.add_line([[0, 0], [1, 1]])
    viewer.drag_tool.active = DragMode.POLYGON
    viewer.drag_tool.tool.add_point((0.5, 0.5))
    viewer.drag_tool.tool.visible = True

    _right_click(qtbot, viewer)
    assert opened_menus == []
    assert not viewer.drag_tool.tool.visible

    _right_click(qtbot, viewer)
    assert len(opened_menus) == 1


def test_host_can_extend_menu(
    make_napari_plot_viewer: ty.Callable, qtbot: QtBot, opened_menus: list[dict[str, QAction]]
) -> None:
    """Hosts add their own commands through ``evt_canvas_menu``."""
    viewer = make_napari_plot_viewer(show=True)
    viewer.window._qt_viewer.evt_canvas_menu.connect(lambda menu: menu.addAction("Extra").setObjectName("extra"))
    _right_click(qtbot, viewer)
    assert "extra" in opened_menus[0]
