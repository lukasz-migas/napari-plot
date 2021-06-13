"""Toolbar"""
# Third-party imports
from napari.utils.events.event import EmitterGroup, Event
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget

from imimsui._napari.line.layers.region._region_constants import Mode as RegionMode
from imimsui._qt.qt_mini_toolbar import QtMiniToolbar  # noqa
from imimsui.gui_elements.dialog_preferences import show_line_config

# Local imports
from imimsui.gui_elements.helpers import make_radio_btn_group, qt_signals_blocked


class QtViewToolbar(QWidget):
    """Qt toolbars"""

    # dialogs
    _dlg_shapes, _dlg_region = None, None

    def __init__(self, view, viewer, qt_viewer, **kwargs):
        super().__init__(parent=qt_viewer)
        self.view = view
        self.viewer = viewer
        self.qt_viewer = qt_viewer
        self.allow_extraction = kwargs.get("allow_extraction", True)

        self.events = EmitterGroup(
            auto_connect=False,
            selection_off=Event,
            # shapes events
            shapes_extract=Event,
            shapes_cancel=Event,
            # region events
            region_open=Event,
            region_extract=Event,
            region_moved=Event,
            region_add=Event,
            region_cancel=Event,
        )
        # connect events
        self.events.region_cancel.connect(self._on_close_extract_layer)
        self.events.selection_off.connect(self._on_close_extract_layer)

        # create instance
        toolbar_left, toolbar_right = QtMiniToolbar(
            qt_viewer, Qt.Vertical
        ), QtMiniToolbar(qt_viewer, Qt.Vertical)
        self.toolbar_left = toolbar_left
        self.toolbar_right = toolbar_right

        # right-hand toolbar
        # view reset/clear
        self.tools_erase_btn = toolbar_right.insert_svg_tool(
            "erase", tooltip="Clear image", func=viewer.clear_canvas
        )
        self.tools_zoomout_btn = toolbar_right.insert_svg_tool(
            "zoom_out", tooltip="Zoom-out", func=viewer.reset_view
        )
        # view modifiers
        toolbar_right.insert_separator()
        self.tools_clip_btn = toolbar_right.insert_svg_tool(
            "clipboard",
            tooltip="Copy figure to clipboard",
            func=self.qt_viewer.clipboard,
        )
        self.tools_save_btn = toolbar_right.insert_svg_tool(
            "save", tooltip="Save figure", func=self.qt_viewer.on_save_figure
        )
        self.tools_settings_btn = toolbar_right.insert_svg_tool(
            "settings", tooltip="Settings configuration", set_checkable=False
        )
        self.tools_settings_btn.evt_click.connect(show_line_config)
        self.tools_axes_btn = toolbar_right.insert_svg_tool(
            "axes_label",
            tooltip="Show axes controls",
            set_checkable=False,
        )
        self.tools_axes_btn.evt_click.connect(self.on_open_axes_config)
        self.tools_text_btn = toolbar_right.insert_svg_tool(
            "text",
            tooltip="Show/hide text label",
            set_checkable=True,
        )
        self.tools_text_btn.connect_to_right_click(self.on_open_text_config)
        self.tools_grid_btn = toolbar_right.insert_svg_tool(
            "grid",
            tooltip="Show/hide grid",
            set_checkable=True,
        )
        self.layers_btn = toolbar_right.insert_svg_tool(
            "layers",
            tooltip="Display layer controls",
            set_checkable=False,
            func=qt_viewer.on_toggle_controls_dialog,
        )

        # left-hand toolbar
        # this branch provides additional tools in the toolbar to allow extraction
        if self.allow_extraction:
            self.tools_region_btn = toolbar_left.insert_svg_tool(
                "extract",
                tooltip="Click here to enter extraction mode",
                set_checkable=True,
                func=self.on_open_extract_region_layer,
            )
            self.tools_off_btn = toolbar_left.insert_svg_tool(
                "none",
                tooltip="Disable data extraction (default)",
                set_checkable=True,
                func=self._on_close_extract_layer,
            )
            self.tools_off_btn.setChecked(True)
            _radio_group = make_radio_btn_group(
                qt_viewer,
                [self.tools_region_btn, self.tools_off_btn],
            )
        self.zoom_btn = toolbar_left.insert_svg_tool(
            "zoom",
            tooltip="Zoom-in on region of interest",
            set_checkable=False,
            func=self.on_open_zoom,
        )
        if toolbar_left.n_items == 0:
            toolbar_left.setVisible(False)
        if toolbar_right.n_items == 0:
            toolbar_right.setVisible(False)

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

    def on_open_zoom(self):
        """Open zoom dialog"""
        from imimsui.gui_elements.dialog_misc import XZoomPopup

        dlg = XZoomPopup(self.viewer, self)
        dlg.show_right_of_mouse()

    def on_open_text_config(self):
        """Open text config"""
        from imimsui._napari.common.layer_controls.qt_text_overlay_controls import (
            QtTextOverlayControls,
        )

        dlg = QtTextOverlayControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_axes_config(self):
        """Open scalebar config"""
        from imimsui._napari.line.layer_controls.qt_axis_controls import QtAxisControls

        dlg = QtAxisControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_extract_region_layer(self):
        """Fully instantiate extract mask layer"""
        from imimsui.gui_elements.dialog_misc import LineRegionROIExtractPopup

        # create blank labels layer
        layer = self.view.add_extract_region_layer()
        try:
            self._dlg_region.setVisible(True)
        except (AttributeError, RuntimeError):
            self._dlg_region = LineRegionROIExtractPopup(self, self.view, layer)
            self._dlg_region.show_right_of_widget(self.tools_grid_btn)
        layer.mode = (
            RegionMode.SELECT
        )  # auto-select the paint layer so the user can simply draw on the canvas
        self.events.region_open(layer=layer)

    def _on_close_extract_region_layer(self, _evt=None):
        """Close shapes layer"""
        layer = self.view.region_layer
        # remove layer from the list
        if layer is not None:
            self.view.remove_layer(layer.name)
        self._dlg_region = None

    def _on_close_extract_layer(self, _evt=None):
        """Close layer"""
        if self._dlg_region is not None:
            self._on_close_extract_region_layer()

        with qt_signals_blocked(self.tools_off_btn):
            self.tools_off_btn.setChecked(True)
