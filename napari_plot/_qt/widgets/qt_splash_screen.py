from qtpy.QtCore import Qt
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QSplashScreen

from napari_plot._qt.qt_event_loop import NAPARI_PLOT_ICON_PATH, get_app


class QtSplashScreen(QSplashScreen):
    """Splash screen for napari_plot."""

    def __init__(self, width=360):
        get_app()
        pm = QPixmap(str(NAPARI_PLOT_ICON_PATH)).scaled(
            width,
            width,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        super().__init__(pm)
        self.show()
