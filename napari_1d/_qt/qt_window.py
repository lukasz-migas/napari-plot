import typing as ty
from qtpy.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QVBoxLayout, QWidget
from ..components.viewer_model import ViewerModel
from .qt_viewer import QtViewer


def make_window(horizontal: bool = True, show: bool = True) -> ty.Tuple[ViewerModel, QtViewer, QMainWindow]:
    """Make window"""
    QApplication()
    main = QMainWindow()

    viewer1d = ViewerModel()
    widget = QtViewer(viewer1d)

    if horizontal:
        layout = QHBoxLayout()
    else:
        layout = QVBoxLayout()
    layout.addWidget(widget)
    main.setCentralWidget(QWidget())
    main.centralWidget().setLayout(layout)
    if show:
        main.show()
    return viewer1d, widget, main
