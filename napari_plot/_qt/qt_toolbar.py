"""Toolbar"""

import typing as ty
from weakref import ref

import qtextra.helpers as hp
from qtextra.widgets.qt_toolbar_mini import QtMiniToolbar
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QAction, QMenu, QWidget

if ty.TYPE_CHECKING:
    from napari_plot._qt.qt_viewer import QtViewer
    from napari_plot.viewer import Viewer


class QtViewToolbar(QWidget):
    """Qt toolbars"""

    # dialogs
    _dlg_axis = None

    def __init__(self, viewer: "Viewer", qt_viewer: "QtViewer", **kwargs):
        super().__init__(parent=qt_viewer)
        self.ref_viewer = ref(viewer)
        self.ref_qt_viewer = ref(qt_viewer)

        # create instance
        toolbar_right = QtMiniToolbar(qt_viewer, Qt.Orientation.Vertical)
        self.toolbar_right = toolbar_right
        # view reset/clear
        self.tools_erase_btn = toolbar_right.insert_qta_tool("erase", tooltip="Clear image", func=self._clear_canvas)
        self.tools_zoomout_btn = toolbar_right.insert_qta_tool("zoom_out", tooltip="Zoom-out", func=self._reset_view)
        # view modifiers
        self.tools_clip_btn = toolbar_right.insert_qta_tool(
            "screenshot",
            tooltip="Copy figure to clipboard",
            func=self.ref_qt_viewer().clipboard,
        )
        self.tools_camera_btn = toolbar_right.insert_qta_tool(
            "zoom",
            tooltip="Show camera controls",
            checkable=False,
            func=self._toggle_camera_controls,
        )
        self.tools_axis_btn = toolbar_right.insert_qta_tool(
            "axes",
            tooltip="Show axis controls",
            checkable=False,
            func=self._toggle_axis_visible,
        )
        self.tools_text_btn = toolbar_right.insert_qta_tool(
            "text",
            tooltip="Show/hide text label",
            checkable=True,
            func=self._toggle_text_visible,
        )
        self.tools_grid_btn = toolbar_right.insert_qta_tool(
            "grid",
            tooltip="Show/hide grid",
            checkable=True,
            func=self._toggle_grid_lines_visible,
        )
        self.tools_tool_btn = toolbar_right.insert_qta_tool(
            "tool",
            tooltip="Select current tool.",
            func=self._open_tools_menu,
        )
        self.layers_btn = toolbar_right.insert_qta_tool(
            "layers",
            tooltip="Display layer controls",
            checkable=False,
            func=self.ref_qt_viewer().on_toggle_controls_dialog,
        )

    def _clear_canvas(self):
        self.ref_viewer().clear_canvas()

    def _reset_view(self):
        self.ref_viewer().reset_view()

    def _toggle_grid_lines_visible(self, state):
        self.ref_qt_viewer().viewer.grid_lines.visible = state

    def _toggle_text_visible(self, state):
        self.ref_qt_viewer().viewer.text_overlay.visible = state

    def _toggle_axis_visible(self, state):
        self.ref_qt_viewer().viewer.axis.visible = state

    def _toggle_axis_controls(self, _):
        from napari_plot._qt.component_controls.qt_axis_controls import QtAxisControls

        dlg = QtAxisControls(self.ref_viewer(), self.ref_qt_viewer())
        dlg.show_left_of_widget(self.tools_axis_btn, x_offset=dlg.width() * 2)

    def _toggle_camera_controls(self, _):
        from napari_plot._qt.component_controls.qt_camera_controls import (
            QtCameraControls,
        )

        dlg = QtCameraControls(self.ref_viewer(), self.ref_qt_viewer())
        dlg.show_left_of_widget(self.tools_camera_btn, x_offset=dlg.width() * 2)

    def _open_tools_menu(self):
        """Open menu of available tools."""
        hp.show_menu(menu=create_tools_menu(self))


def create_tools_menu(parent: "QtViewToolbar") -> QMenu:
    """Create a menu of available tools."""
    from napari_plot.components.dragtool import DragMode

    menu = QMenu(parent)
    actions = []
    toggle_tool = QAction("Tool: Auto (zoom)", parent)
    toggle_tool.setCheckable(True)
    toggle_tool.setChecked(parent.ref_qt_viewer().viewer.drag_tool.active == DragMode.AUTO)
    toggle_tool.triggered.connect(lambda: setattr(parent.ref_qt_viewer().viewer.drag_tool, "active", DragMode.AUTO))
    menu.addAction(toggle_tool)
    actions.append(toggle_tool)

    toggle_tool = QAction("Tool: Auto (zoom + trigger)", parent)
    toggle_tool.setCheckable(True)
    toggle_tool.setChecked(parent.ref_qt_viewer().viewer.drag_tool.active == DragMode.AUTO_TRIGGER)
    toggle_tool.triggered.connect(
        lambda: setattr(parent.ref_qt_viewer().viewer.drag_tool, "active", DragMode.AUTO_TRIGGER)
    )
    menu.addAction(toggle_tool)
    actions.append(toggle_tool)

    toggle_tool = QAction("Tool: Box (zoom + trigger)", parent)
    toggle_tool.setCheckable(True)
    toggle_tool.setChecked(parent.ref_qt_viewer().viewer.drag_tool.active == DragMode.BOX)
    toggle_tool.triggered.connect(lambda: setattr(parent.ref_qt_viewer().viewer.drag_tool, "active", DragMode.BOX))
    menu.addAction(toggle_tool)
    actions.append(toggle_tool)

    toggle_tool = QAction("Tool: Horizontal span (zoom + trigger)", parent)
    toggle_tool.setCheckable(True)
    toggle_tool.setChecked(parent.ref_qt_viewer().viewer.drag_tool.active == DragMode.HORIZONTAL_SPAN)
    toggle_tool.triggered.connect(
        lambda: setattr(
            parent.ref_qt_viewer().viewer.drag_tool,
            "active",
            DragMode.HORIZONTAL_SPAN,
        )
    )
    menu.addAction(toggle_tool)
    actions.append(toggle_tool)

    toggle_tool = QAction("Tool: Vertical span (zoom)", parent)
    toggle_tool.setCheckable(True)
    toggle_tool.setChecked(parent.ref_qt_viewer().viewer.drag_tool.active == DragMode.VERTICAL_SPAN)
    toggle_tool.triggered.connect(
        lambda: setattr(parent.ref_qt_viewer().viewer.drag_tool, "active", DragMode.VERTICAL_SPAN)
    )
    menu.addAction(toggle_tool)
    actions.append(toggle_tool)

    toggle_tool = QAction("Select tool: Box (select)", parent)
    toggle_tool.setCheckable(True)
    toggle_tool.setChecked(parent.ref_qt_viewer().viewer.drag_tool.active == DragMode.BOX_SELECT)
    toggle_tool.triggered.connect(
        lambda: setattr(parent.ref_qt_viewer().viewer.drag_tool, "active", DragMode.BOX_SELECT)
    )
    menu.addAction(toggle_tool)
    actions.append(toggle_tool)

    toggle_tool = QAction("Select tool: Polygon (select)", parent)
    toggle_tool.setCheckable(True)
    toggle_tool.setChecked(parent.ref_qt_viewer().viewer.drag_tool.active == DragMode.POLYGON)
    toggle_tool.triggered.connect(lambda: setattr(parent.ref_qt_viewer().viewer.drag_tool, "active", DragMode.POLYGON))
    menu.addAction(toggle_tool)
    actions.append(toggle_tool)

    toggle_tool = QAction("Select tool: Lasso (select)", parent)
    toggle_tool.setCheckable(True)
    toggle_tool.setChecked(parent.ref_qt_viewer().viewer.drag_tool.active == DragMode.LASSO)
    toggle_tool.triggered.connect(lambda: setattr(parent.ref_qt_viewer().viewer.drag_tool, "active", DragMode.LASSO))
    menu.addAction(toggle_tool)
    actions.append(toggle_tool)

    # ensures that only single tool can be selected at at ime
    hp.make_menu_group(parent, *actions)
    return menu
