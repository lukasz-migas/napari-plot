"""Regression tests for opening and using layer-list context menus."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import numpy as np
import pytest
from app_model.backends.qt import QModelMenu
from napari._app_model import get_app_model
from napari.components import LayerList
from napari.layers import Image, Layer, Points, Shapes
from pytestqt.qtbot import QtBot
from qtpy.QtCore import QEvent, QPoint, QPointF, Qt
from qtpy.QtGui import QAction, QMouseEvent
from qtpy.QtWidgets import QMenu, QStyleOptionViewItem

from napari_plot._qt.qt_layer_list import QtLayerList
from napari_plot.layers import Bar, Centroids, InfLine, Line, MultiLine, Region, Scatter, Text


def _menu_actions(menu: QMenu) -> Iterator[QAction]:
    """Yield commands from a context menu and its submenus."""
    for action in menu.actions():
        yield action
        if submenu := action.menu():
            yield from _menu_actions(submenu)


def _right_click_menu(
    qtbot: QtBot, view: QtLayerList, monkeypatch: pytest.MonkeyPatch, command: str | None = None
) -> list[QAction]:
    """Construct the real context menu, replacing only its blocking modal execution."""
    actions: list[QAction] = []

    def use_menu(menu: QModelMenu, _position: QPoint) -> None:
        actions.extend(_menu_actions(menu))
        if command is not None:
            next(action for action in actions if action.objectName() == command).trigger()

    with monkeypatch.context() as patcher, qtbot.captureExceptions() as exceptions:
        patcher.setattr(QModelMenu, "exec", use_menu)
        index = view.model().index(0, 0)
        option = QStyleOptionViewItem()
        option.widget = view
        option.rect = view.visualRect(index)
        point = option.rect.center()
        event = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(point),
            QPointF(view.viewport().mapToGlobal(point)),
            Qt.MouseButton.RightButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        result = view.itemDelegate().editorEvent(event, view.model(), option, index)
        assert isinstance(result, bool)
    assert not exceptions
    assert actions, "The right click did not construct the context menu."
    return actions


@pytest.mark.parametrize(
    ("layer_type", "data"),
    [
        (Bar, [1, 2]),
        (Centroids, [[1, 2], [3, 4]]),
        (InfLine, [1, 2]),
        (Line, [[1, 2], [3, 4]]),
        (MultiLine, (np.array([1, 2]), np.array([3, 4]))),
        (Region, [[1, 2]]),
        (Scatter, [[1, 2], [3, 4]]),
        (Text, [[1, 2], [3, 4]]),
        (Image, np.zeros((2, 2))),
        (Points, [[1, 2]]),
        (Shapes, [[[0, 0], [0, 1], [1, 1], [1, 0]]]),
    ],
)
def test_right_click_opens_layer_context_menu(
    layer_type: type[Layer], data: Any, make_napari_plot_viewer: Callable, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every plot and built-in layer can open the actual menu without Qt exceptions."""
    viewer = make_napari_plot_viewer()
    viewer.add_layer(layer_type(data))
    actions = _right_click_menu(qtbot, viewer.window._qt_viewer.layers, monkeypatch)

    assert any(action.objectName() == "napari.layer.duplicate" for action in actions)
    assert any(action.objectName() == "napari.layer.bounding_box" for action in actions)


def test_context_menu_targets_clicked_plot(
    make_napari_plot_viewer: Callable, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Menu commands target the clicked plot even when a different plot is current."""
    clicked = make_napari_plot_viewer()
    clicked_layer = clicked.add_line([[0, 0], [1, 1]])
    other = make_napari_plot_viewer()
    other_layer = other.add_line([[2, 2], [3, 3]])
    store = get_app_model().injection_store
    providers_before = list(store.iter_providers(LayerList))

    _right_click_menu(qtbot, clicked.window._qt_viewer.layers, monkeypatch, "napari.layer.toggle_visibility")

    assert not clicked_layer.visible
    assert other_layer.visible
    assert list(store.iter_providers(LayerList)) == providers_before

    _right_click_menu(qtbot, clicked.window._qt_viewer.layers, monkeypatch, "napari.layer.toggle_visibility")

    assert clicked_layer.visible
    assert other_layer.visible
    assert list(store.iter_providers(LayerList)) == providers_before


def test_context_menu_keeps_host_napari_providers(
    make_napari_viewer: Callable, make_napari_plot_viewer: Callable, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plot popup commands leave the host napari viewer and its providers intact."""
    host = make_napari_viewer(strict_qt=False)
    host_layer = host.add_points([[0, 0]])
    plot = make_napari_plot_viewer()
    plot_layer = plot.add_scatter([[1, 2]])
    store = get_app_model().injection_store
    providers_before = list(store.iter_providers(LayerList))

    _right_click_menu(qtbot, plot.window._qt_viewer.layers, monkeypatch, "napari.layer.duplicate")

    assert len(plot.layers) == 2
    assert plot.layers[0] is plot_layer
    assert list(host.layers) == [host_layer]
    assert list(store.iter_providers(LayerList)) == providers_before

    copied: dict[str, Any] = {}
    monkeypatch.setattr("napari._qt._qapp_model.qactions._layerlist_context._set_data_in_clipboard", copied.update)
    plot.layers.selection.select_only(plot_layer)
    plot_layer.scale = (2, 3)
    host_layer.scale = (5, 6)
    layer_providers_before = list(store.iter_providers(Layer))

    _right_click_menu(qtbot, plot.window._qt_viewer.layers, monkeypatch, "napari.layer.copy_scale_to_clipboard")

    np.testing.assert_array_equal(copied["scale"], (2, 3))
    assert list(store.iter_providers(Layer)) == layer_providers_before
