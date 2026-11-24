from collections.abc import Callable

from napari_plot._qt.qt_main_window import _QtMainWindow
from napari_plot._qt.qt_toolbar import create_tools_menu
from napari_plot.components.dragtool import DragMode
from napari_plot.viewer import Viewer


def test_current_viewer(make_napari_plot_viewer, qapp):
    """Test that we can retrieve the "current" viewer window easily.

    ... where "current" means it was the last viewer the user interacted with.
    """
    assert _QtMainWindow.current() is None
    # when we create a new viewer it becomes accessible at Viewer.current()
    v1 = make_napari_plot_viewer(title="v1")
    assert _QtMainWindow._instances == [v1.window._qt_window]
    assert _QtMainWindow.current() == v1.window._qt_window

    v2 = make_napari_plot_viewer(title="v2")
    assert _QtMainWindow._instances == [
        v1.window._qt_window,
        v2.window._qt_window,
    ]
    assert _QtMainWindow.current() == v2.window._qt_window

    # Viewer.current() will always give the most recently activated viewer.
    v1.window.activate()
    assert _QtMainWindow.current() == v1.window._qt_window
    v2.window.activate()
    assert _QtMainWindow.current() == v2.window._qt_window

    # The list remembers the z-order of previous viewers ...
    v2.close()
    assert _QtMainWindow.current() == v1.window._qt_window
    assert _QtMainWindow._instances == [v1.window._qt_window]

    # and when none are left, Viewer.current() becomes None again
    v1.close()
    assert _QtMainWindow._instances == []
    assert _QtMainWindow.current() is None


def test_drag_tool_menus_reflect_disabled_tool(make_napari_plot_viewer: Callable[[], Viewer]) -> None:
    """The toolbar can disable the drag tool and the Interaction menu reflects that choice."""
    viewer = make_napari_plot_viewer()
    window = viewer.window
    try:
        menu = create_tools_menu(window._qt_viewer.viewerToolbar)
        no_tool = next(action for action in menu.actions() if action.text() == "No drag tool")
        assert not no_tool.isChecked()
        no_tool.trigger()
        assert viewer.drag_tool.active == DragMode.NONE
        assert viewer.drag_tool.tool is None
        assert window._menu_tool_none.isChecked()
        assert not window._menu_tool_h_span.isChecked()

        window._menu_tool_h_span.trigger()
        assert viewer.drag_tool.active == DragMode.HORIZONTAL_SPAN
        assert viewer.drag_tool.tool is not None
        assert not window._menu_tool_none.isChecked()
    finally:
        viewer.close()
