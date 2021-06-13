"""Toolbar"""
# Third-party imports
from napari.utils.events.event import EmitterGroup, Event
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget

from napari_1d._qt.widgets.qt_mini_toolbar import QtMiniToolbar


class QtViewToolbar(QWidget):
    """Qt toolbars"""

    # dialogs
    _dlg_shapes, _dlg_region = None, None

    def __init__(self, viewer, qt_viewer, **kwargs):
        super().__init__(parent=qt_viewer)
        self.viewer = viewer
        self.qt_viewer = qt_viewer

        self.events = EmitterGroup(auto_connect=False)

        # create instance
        toolbar_right = QtMiniToolbar(qt_viewer, Qt.Vertical)
        self.toolbar_right = toolbar_right
        # self.tools_erase_btn = toolbar_right.insert_svg_tool("erase", tooltip="Clear image", func=viewer.clear_canvas)
        # self.tools_zoomout_btn = toolbar_right.insert_svg_tool("zoom_out", tooltip="Zoom-out", func=viewer.reset_view)
        self.layers_btn = toolbar_right.insert_svg_tool(
            "layers",
            tooltip="Display layer controls",
            set_checkable=False,
            func=qt_viewer.on_toggle_controls_dialog,
        )

    def connect_toolbar(self):
        """Connect events"""
        self.tools_grid_btn.setChecked(self.qt_viewer.viewer.grid_lines.visible)
        self.tools_grid_btn.clicked.connect(self._toggle_grid_lines_visible)
        self.qt_viewer.viewer.grid_lines.events.visible.connect(
            lambda x: self.tools_grid_btn.setChecked(
                self.qt_viewer.viewer.grid_lines.visible
            )
        )

        self.tools_text_btn.setChecked(self.qt_viewer.viewer.text_overlay.visible)
        self.tools_text_btn.clicked.connect(self._toggle_text_visible)
        self.qt_viewer.viewer.text_overlay.events.visible.connect(
            lambda x: self.tools_text_btn.setChecked(
                self.qt_viewer.viewer.text_overlay.visible
            )
        )

    def _toggle_grid_lines_visible(self, state):
        self.qt_viewer.viewer.grid_lines.visible = state

    def _toggle_text_visible(self, state):
        self.qt_viewer.viewer.text_overlay.visible = state
