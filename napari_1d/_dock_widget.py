"""Dock widget"""
from napari_plugin_engine import napari_hook_implementation
from qtpy.QtWidgets import QVBoxLayout, QWidget

from ._qt.qt_viewer import QtViewer
from .components.viewer_model import ViewerModel as ViewerModel1D


class Napari1dWidget(QWidget):
    """Create instance of 1d Viewer"""

    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.viewer1d = ViewerModel1D()
        self.qt_viewer = QtViewer(self.viewer1d)

        layout = QVBoxLayout()
        layout.addWidget(self.qt_viewer, stretch=True)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    """Return dock widget."""
    return Napari1dWidget
