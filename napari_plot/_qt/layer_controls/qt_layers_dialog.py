"""Tool dialog to display layer controls"""
from qtpy.QtWidgets import QVBoxLayout

from ..qt_dialog import QtFramelessTool


class Napari1dControls(QtFramelessTool):
    """Controls display"""

    def __init__(self, qt_viewer):
        self.qt_viewer = qt_viewer
        super().__init__(parent=qt_viewer)

        self.setMinimumHeight(600)

    def make_panel(self) -> QVBoxLayout:
        """Make panel"""
        va = QVBoxLayout()
        va.addLayout(self._make_move_handle())  # noqa
        va.addWidget(self.qt_viewer.controls)
        va.addWidget(self.qt_viewer.layerButtons)
        va.addWidget(self.qt_viewer.layers, stretch=True)
        va.addWidget(self.qt_viewer.viewerButtons)
        return va

    def keyPressEvent(self, event):
        """Called whenever a key is pressed.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self.qt_viewer.canvas._backend._keyEvent(self.qt_viewer.canvas.events.key_press, event)
        event.accept()

    def keyReleaseEvent(self, event):
        """Called whenever a key is released.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self.qt_viewer.canvas._backend._keyEvent(self.qt_viewer.canvas.events.key_release, event)
        event.accept()
