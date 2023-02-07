"""Tool dialog to display layer controls"""
from weakref import ref

from qtpy.QtWidgets import QVBoxLayout

import napari_plot._qt.helpers as hp
from napari_plot._qt.qt_dialog import QtFramelessTool


class NapariPlotControls(QtFramelessTool):
    """Controls display"""

    def __init__(self, qt_viewer):
        self._ref_qt_viewer = ref(qt_viewer)
        super().__init__(parent=qt_viewer)

        self.setMinimumHeight(600)

    def hide_dialog(self):
        """Hide dialog"""
        self.setVisible(False)

    def make_panel(self) -> QVBoxLayout:
        """Make panel"""
        move_layout = self._make_move_handle()

        # this button will only appear if the viewer is not docked and not when it's the main window
        hide_btn = hp.make_qta_btn(self, "close", "Hide control panel.")
        hide_btn.clicked.connect(self.hide_dialog)
        move_layout.addWidget(hide_btn)

        qt_viewer = self._ref_qt_viewer()
        va = QVBoxLayout()
        va.addLayout(move_layout)
        va.addWidget(qt_viewer.controls)
        va.addWidget(qt_viewer.layerButtons)
        va.addWidget(qt_viewer.layers, stretch=True)
        va.addWidget(qt_viewer.viewerButtons)
        return va

    def keyPressEvent(self, event):
        """Called whenever a key is pressed.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self._ref_qt_viewer().canvas._backend._keyEvent(self._ref_qt_viewer().canvas.events.key_press, event)
        event.accept()

    def keyReleaseEvent(self, event):
        """Called whenever a key is released.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self._ref_qt_viewer().canvas._backend._keyEvent(self._ref_qt_viewer().canvas.events.key_release, event)
        event.accept()
