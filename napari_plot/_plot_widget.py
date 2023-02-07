"""Dock widget"""
from qtpy.QtWidgets import QVBoxLayout, QWidget

from napari_plot._qt.helpers import get_parent
from napari_plot._qt.qt_viewer import QtViewer
from napari_plot.components.viewer_model import ViewerModel as ViewerModelPlot


class NapariPlotWidget(QWidget):
    """Create instance of napari-plot Viewer."""

    def __init__(self, napari_viewer):
        parent = get_parent(None)
        super().__init__(parent)
        self.viewer = napari_viewer
        self.viewer_plot = ViewerModelPlot()
        self.qt_viewer = QtViewer(self.viewer_plot, parent=parent)

        layout = QVBoxLayout(self)
        layout.addWidget(self.qt_viewer, stretch=True)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
