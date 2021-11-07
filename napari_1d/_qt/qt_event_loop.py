"""Event loop"""
import os
import sys
from warnings import warn

from napari._qt.dialogs.qt_notification import NapariQtNotification
from napari._qt.qt_event_loop import _ipython_has_eventloop, run  # noqa
from napari._qt.qt_resources import _register_napari_resources
from napari._qt.qthreading import wait_for_workers_to_quit
from napari.plugins import plugin_manager
from napari.utils.notifications import notification_manager, show_console_notification
from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QApplication

from .. import __version__

NAPARI_APP_ID = f"napari_1d.napari_1d.viewer.{__version__}"


def set_app_id(app_id):
    """Get app ID."""
    if os.name == "nt" and app_id and not getattr(sys, "frozen", False):
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)


_defaults = {
    "app_name": "napari",
    "app_version": __version__,
    # "icon": NAPARI_ICON_PATH,
    "org_name": "napari",
    "org_domain": "napari.org",
    "app_id": NAPARI_APP_ID,
}


# store reference to QApplication to prevent garbage collection
_app_ref = None


def get_app(
    *,
    app_name: str = None,
    app_version: str = None,
    icon: str = None,
    org_name: str = None,
    org_domain: str = None,
    app_id: str = None,
    ipy_interactive: bool = None,
) -> QApplication:
    """Get or create the Qt QApplication.

    There is only one global QApplication instance, which can be retrieved by
    calling get_app again, (or by using QApplication.instance())

    Parameters
    ----------
    app_name : str, optional
        Set app name (if creating for the first time), by default 'napari'
    app_version : str, optional
        Set app version (if creating for the first time), by default __version__
    icon : str, optional
        Set app icon (if creating for the first time), by default
        NAPARI_ICON_PATH
    org_name : str, optional
        Set organization name (if creating for the first time), by default
        'napari'
    org_domain : str, optional
        Set organization domain (if creating for the first time), by default
        'napari.org'
    app_id : str, optional
        Set organization domain (if creating for the first time).  Will be
        passed to set_app_id (which may also be called independently), by
        default NAPARI_APP_ID
    ipy_interactive : bool, optional
        Use the IPython Qt event loop ('%gui qt' magic) if running in an
        interactive IPython terminal.

    Returns
    -------
    QApplication
        [description]

    Notes
    -----
    Substitutes QApplicationWithTracing when the NAPARI_PERFMON env variable
    is set.

    If the QApplication already exists, we call convert_app_for_tracing() which
    deletes the QApplication and creates a new one. However here with get_app
    we need to create the correct QApplication up front, or we will crash
    because we'd be deleting the QApplication after we created QWidgets with
    it, such as we do for the splash screen.
    """
    # napari defaults are all-or nothing.  If any of the keywords are used
    # then they are all used.
    set_values = {k for k, v in locals().items() if v}
    kwargs = locals() if set_values else _defaults
    global _app_ref

    app = QApplication.instance()
    if app:
        set_values.discard("ipy_interactive")
        if set_values:

            warn(
                f"QApplication already existed, these arguments to to 'get_app' were ignored: {set_values}",
            )
    else:
        # automatically determine monitor DPI.
        # Note: this MUST be set before the QApplication is instantiated
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        app = QApplication(sys.argv)

        # if this is the first time the Qt app is being instantiated, we set
        # the name and metadata
        app.setApplicationName(kwargs.get("app_name"))
        app.setApplicationVersion(kwargs.get("app_version"))
        app.setOrganizationName(kwargs.get("org_name"))
        app.setOrganizationDomain(kwargs.get("org_domain"))
        set_app_id(kwargs.get("app_id"))

    if not _ipython_has_eventloop():
        notification_manager.notification_ready.connect(NapariQtNotification.show_notification)
        notification_manager.notification_ready.connect(show_console_notification)

    if app.windowIcon().isNull():
        app.setWindowIcon(QIcon(kwargs.get("icon")))

    if not _app_ref:  # running get_app for the first time
        # see docstring of `wait_for_workers_to_quit` for caveats on killing
        # workers at shutdown.
        app.aboutToQuit.connect(wait_for_workers_to_quit)

        try:
            # this will register all of our resources (icons) with Qt, so that they
            # can be used in qss files and elsewhere.
            plugin_manager.discover_icons()
            plugin_manager.discover_qss()
        except AttributeError:
            pass
        _register_napari_resources()

    _app_ref = app  # prevent garbage collection

    return app


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
