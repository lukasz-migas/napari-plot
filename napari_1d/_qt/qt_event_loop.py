"""Event loop"""
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QApplication
from napari._qt.qt_event_loop import _ipython_has_eventloop, run  # noqa


def quit_app():
    """Close all windows and quit the QApplication if napari started it."""
    QApplication.closeAllWindows()
    # if we started the application then the app will be named 'napari'.
    if QApplication.applicationName() == "napari-1d" and not _ipython_has_eventloop():
        QApplication.quit()

    # otherwise, something else created the QApp before us (such as
    # %gui qt IPython magic).  If we quit the app in this case, then
    # *later* attempts to instantiate a napari viewer won't work until
    # the event loop is restarted with app.exec_().  So rather than
    # quit just close all the windows (and clear our app icon).
    else:
        QApplication.setWindowIcon(QIcon())
