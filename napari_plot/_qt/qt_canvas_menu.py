"""Right-click menu of the plot canvas."""

from __future__ import annotations

import typing as ty

import qtextra.helpers as hp
from qtpy.QtWidgets import QMenu

from napari_plot.components._viewer_key_bindings import TOOL_SHORTCUTS
from napari_plot.components.dragtool import DragMode

if ty.TYPE_CHECKING:
    from napari_plot._qt.qt_viewer import QtViewer

# tools listed in the menu, with their labels; the shortcut is shown after a tab (display only, not bound here)
TOOL_LABELS: dict[DragMode, str] = {
    DragMode.NONE: "No drag tool",
    DragMode.AUTO: "Auto (zoom)",
    DragMode.BOX: "Box (zoom)",
    DragMode.VERTICAL_SPAN: "Vertical span (zoom x)",
    DragMode.HORIZONTAL_SPAN: "Horizontal span (zoom y)",
    DragMode.BOX_SELECT: "Box (select)",
    DragMode.LASSO: "Lasso (select)",
    DragMode.POLYGON: "Polygon (select)",
}


def _label(text: str, shortcut: str | None) -> str:
    return f"{text}\t{shortcut}" if shortcut else text


def build_canvas_menu(qt_viewer: QtViewer) -> QMenu:
    """Return the canvas context menu: view resets, drag tools, overlay toggles and export."""
    viewer = qt_viewer.viewer
    menu = QMenu(qt_viewer)

    hp.make_menu_item(menu, _label("Reset view", "Home"), menu=menu, func=lambda: viewer.reset_view())
    hp.make_menu_item(menu, "Reset x-axis", menu=menu, func=lambda: viewer.reset_x_view())
    hp.make_menu_item(menu, "Reset y-axis", menu=menu, func=lambda: viewer.reset_y_view())
    menu.addSeparator()

    tools = hp.make_menu(menu, "Tool", menu=menu)
    actions = []
    for mode, text in TOOL_LABELS.items():
        action = hp.make_menu_item(
            tools,
            _label(text, TOOL_SHORTCUTS.get(mode)),
            menu=tools,
            checkable=True,
            checked=viewer.drag_tool.active == mode,
            func=lambda _=False, mode=mode: setattr(viewer.drag_tool, "active", mode),
        )
        action.setObjectName(f"napari_plot.canvas.tool.{mode.value}")
        actions.append(action)
    hp.make_menu_group(tools, *actions)

    for name, text, overlay in (
        ("grid_lines", _label("Grid lines", "Ctrl+G"), viewer.grid_lines),
        ("legend", "Legend", viewer.legend),
        ("crosshair", _label("Crosshair", "C"), viewer.crosshair),
        ("hover", _label("Hover readout", "H"), viewer.hover),
    ):
        action = hp.make_menu_item(
            menu,
            text,
            menu=menu,
            checkable=True,
            checked=overlay.visible,
            func=lambda checked, overlay=overlay: setattr(overlay, "visible", checked),
        )
        action.setObjectName(f"napari_plot.canvas.{name}")
    menu.addSeparator()

    hp.make_menu_item(
        menu, _label("Copy to clipboard", "Alt+C"), menu=menu, func=lambda: qt_viewer.clipboard()
    ).setObjectName("napari_plot.canvas.clipboard")
    hp.make_menu_item(
        menu, _label("Save screenshot...", "Alt+S"), menu=menu, func=lambda: qt_viewer._screenshot_dialog()
    ).setObjectName("napari_plot.canvas.screenshot")
    return menu
