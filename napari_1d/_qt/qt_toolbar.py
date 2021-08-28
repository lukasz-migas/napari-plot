"""Toolbar"""
# Third-party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget

from .layer_controls.qt_axis_controls import QtAxisControls
from .widgets.qt_mini_toolbar import QtMiniToolbar


class QtViewToolbar(QWidget):
    """Qt toolbars"""

    # dialogs
    _dlg_axis = None

    def __init__(self, viewer, qt_viewer, **kwargs):
        super().__init__(parent=qt_viewer)
        self.viewer = viewer
        self.qt_viewer = qt_viewer

        # create instance
        toolbar_right = QtMiniToolbar(qt_viewer, Qt.Vertical)
        self.toolbar_right = toolbar_right
        # view reset/clear
        self.tools_erase_btn = toolbar_right.insert_svg_tool("erase", tooltip="Clear image", func=self._clear_canvas)
        self.tools_zoomout_btn = toolbar_right.insert_svg_tool("zoom_out", tooltip="Zoom-out", func=self._reset_view)
        # view modifiers
        self.tools_clip_btn = toolbar_right.insert_svg_tool(
            "clipboard", tooltip="Copy figure to clipboard", func=self.qt_viewer.clipboard
        )
        self.tools_axis_btn = toolbar_right.insert_svg_tool(
            "axes",
            tooltip="Show axis controls",
            set_checkable=False,
            func=self._toggle_axis_controls,
        )
        self.tools_text_btn = toolbar_right.insert_svg_tool(
            "text",
            tooltip="Show/hide text label",
            set_checkable=True,
            func=self._toggle_text_visible,
        )
        self.tools_grid_btn = toolbar_right.insert_svg_tool(
            "plot_grid",
            tooltip="Show/hide grid",
            set_checkable=True,
            func=self._toggle_grid_lines_visible,
        )
        self.layers_btn = toolbar_right.insert_svg_tool(
            "layers",
            tooltip="Display layer controls",
            set_checkable=False,
            func=qt_viewer.on_toggle_controls_dialog,
        )

    def _clear_canvas(self):
        self.viewer.clear_canvas()

    def _reset_view(self):
        self.viewer.reset_view()

    def _toggle_grid_lines_visible(self, state):
        self.qt_viewer.viewer.grid_lines.visible = state

    def _toggle_text_visible(self, state):
        self.qt_viewer.viewer.text_overlay.visible = state

    def _toggle_axis_controls(self, _):
        _dlg_axis = QtAxisControls(self.viewer, self.qt_viewer)
        _dlg_axis.show_left_of_widget(self.tools_axis_btn)
