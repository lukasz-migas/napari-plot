"""Native window."""
import time
import typing as ty

from qtpy.QtCore import QEventLoop
from qtpy.QtWidgets import QApplication, QDialog
from qtpy.QtCore import QEvent
from qtpy.QtGui import QIcon, Qt
from qtpy.QtWidgets import QMainWindow, QWidget, QHBoxLayout

from .qt_event_loop import quit_app
from .qt_viewer import QtViewer


class _QtMainWindow(QMainWindow):
    """Main window."""

    # To track window instances and facilitate getting the "active" viewer...
    # We use this instead of QApplication.activeWindow for compatibility with
    # IPython usage. When you activate IPython, it will appear that there are
    # *no* active windows, so we want to track the most recently active windows
    _instances: ty.ClassVar[ty.List["_QtMainWindow"]] = []

    def __init__(self, qt_viewer: QtViewer, parent=None) -> None:
        super().__init__(parent)
        self._ev = None
        self.qt_viewer = qt_viewer

        self._quit_app = False
        self.setWindowIcon(QIcon(self._window_icon))
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setUnifiedTitleAndToolBarOnMac(True)
        center = QWidget(self)
        center.setLayout(QHBoxLayout())
        center.layout().addWidget(qt_viewer)
        center.layout().setContentsMargins(4, 0, 4, 0)
        self.setCentralWidget(center)
        self.setWindowTitle(qt_viewer.viewer.title)
        _QtMainWindow._instances.append(self)

    @classmethod
    def current(cls):
        return cls._instances[-1] if cls._instances else None

    def event(self, e):
        if e.type() == QEvent.Close:
            # when we close the MainWindow, remove it from the instances list
            try:
                _QtMainWindow._instances.remove(self)
            except ValueError:
                pass
        if e.type() in {QEvent.WindowActivate, QEvent.ZOrderChange}:
            # upon activation or raise_, put window at the end of _instances
            try:
                inst = _QtMainWindow._instances
                inst.append(inst.pop(inst.index(self)))
            except ValueError:
                pass
        return super().event(e)

    # noinspection PyShadowingNames
    def close(self, quit_app=False):
        """Override to handle closing app or just the window."""
        self._quit_app = quit_app
        return super().close()

    def close_window(self):
        """Close active dialog or active window."""
        parent = QApplication.focusWidget()
        while parent is not None:
            if isinstance(parent, QMainWindow):
                self.close()
                break

            if isinstance(parent, QDialog):
                parent.close()
                break

            try:
                parent = parent.parent()
            except Exception:
                parent = getattr(parent, "_parent", None)

    def show(self, block=False):
        super().show()
        if block:
            self._ev = QEventLoop()
            self._ev.exec()

    def closeEvent(self, event):
        """This method will be called when the main window is closing.

        Regardless of whether cmd Q, cmd W, or the close button is used...
        """
        if self._ev and self._ev.isRunning():
            self._ev.quit()

        # On some versions of Darwin, exiting while fullscreen seems to tickle
        # some bug deep in NSWindow.  This forces the fullscreen keybinding
        # test to complete its draw cycle, then pop back out of fullscreen.
        if self.isFullScreen():
            self.showNormal()
            for _i in range(5):
                time.sleep(0.1)
                QApplication.processEvents()

        if self._quit_app:
            quit_app()
        event.accept()
