"""Event loop"""

import logging
import os
import sys
from typing import Optional
from warnings import warn

from napari._qt.dialogs.qt_notification import NapariQtNotification
from napari._qt.qt_event_filters import QtToolTipEventFilter
from napari._qt.qt_event_loop import (
    _ipython_has_eventloop,
    _pycharm_has_eventloop,
    _try_enable_ipython_gui,
)
from napari._qt.qthreading import wait_for_workers_to_quit
from napari._qt.utils import _maybe_allow_interrupt
from napari.resources._icons import _theme_path
from napari.settings import get_settings
from napari.utils.notifications import notification_manager, show_console_notification
from napari.utils.theme import _themes, build_theme_svgs
from qtextra.config.theme import THEMES
from qtpy import PYQT5, PYSIDE2
from qtpy.QtCore import QDir, Qt
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QApplication

from napari_plot import __version__
from napari_plot.viewer import Viewer

NAPARI_PLOT_ICON_PATH = os.path.join(
    os.path.dirname(__file__), "..", "resources", "logo.png"
)
NAPARI_APP_ID = f"napari_plot.napari_plot.viewer.{__version__}"


logger = logging.getLogger()


def set_app_id(app_id):
    """Get app ID."""
    if os.name == "nt" and app_id and not getattr(sys, "frozen", False):
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)


_defaults = {
    "app_name": "napari_plot",
    "app_version": __version__,
    "icon": NAPARI_PLOT_ICON_PATH,
    "org_name": "napari_plot",
    "org_domain": "",
    "app_id": NAPARI_APP_ID,
}


# store reference to QApplication to prevent garbage collection
_app_ref = None
_IPYTHON_WAS_HERE_FIRST = "IPython" in sys.modules


def get_app(
    *,
    app_name: Optional[str] = None,
    app_version: Optional[str] = None,
    icon: Optional[str] = None,
    org_name: Optional[str] = None,
    org_domain: Optional[str] = None,
    app_id: Optional[str] = None,
    ipy_interactive: Optional[bool] = None,
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
        # Note: this MUST be set before the QApplication is instantiated. Also, this
        # attributes need to be applied only to Qt5 bindings (PyQt5 and PySide2)
        # since the High DPI scaling attributes are deactivated by default while on Qt6
        # they are deprecated and activated by default. For more info see:
        # https://doc.qt.io/qtforpython-6/gettingstarted/porting_from2.html#class-function-deprecations
        if PYQT5 or PYSIDE2:
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
        argv = sys.argv.copy()
        if sys.platform == "darwin" and not argv[0].endswith("napari_plot"):
            # Make sure the app name in the Application menu is `napari`
            # which is taken from the basename of sys.argv[0]; we use
            # a copy so the original value is still available at sys.argv
            argv[0] = "napari_plot"
        app = QApplication(argv)

        # if this is the first time the Qt app is being instantiated, we set
        # the name and metadata
        app.setApplicationName(kwargs.get("app_name"))
        app.setApplicationVersion(kwargs.get("app_version"))
        app.setOrganizationName(kwargs.get("org_name"))
        app.setOrganizationDomain(kwargs.get("org_domain"))
        set_app_id(kwargs.get("app_id"))

        # Intercept tooltip events in order to convert all text to rich text
        # to allow for text wrapping of tooltips
        app.installEventFilter(QtToolTipEventFilter())

    if app.windowIcon().isNull():
        app.setWindowIcon(QIcon(kwargs.get("icon")))

    # if ipy_interactive is None:
    #     ipy_interactive = get_settings().application.ipy_interactive
    if _IPYTHON_WAS_HERE_FIRST:
        _try_enable_ipython_gui("qt" if ipy_interactive else None)

    if not _ipython_has_eventloop():
        notification_manager.notification_ready.connect(
            NapariQtNotification.show_notification
        )
        notification_manager.notification_ready.connect(show_console_notification)

    # necessary to ensure that the theme svgs are rebuilt
    for theme in _themes.values():
        build_theme_svgs(theme.id, "builtin")  # source is not correct here!

    if not _app_ref:  # running get_app for the first time
        # see docstring of `wait_for_workers_to_quit` for caveats on killing
        # workers at shutdown.
        app.aboutToQuit.connect(wait_for_workers_to_quit)

        # Setup search paths for currently installed themes.
        for name in _themes:
            QDir.addSearchPath(f"theme_{name}", str(_theme_path(name)))

    # synchronize themes
    THEMES.theme = get_settings().appearance.theme
    _app_ref = app  # prevent garbage collection

    return app


def quit_app():
    """Close all windows and quit the QApplication if napari started it."""
    for v in list(Viewer._instances):
        v.close()
    QApplication.closeAllWindows()
    # if we started the application then the app will be named 'napari'.
    if QApplication.applicationName() == "napari-plot" and not _ipython_has_eventloop():
        QApplication.quit()
    # otherwise, something else created the QApp before us (such as
    # %gui qt IPython magic).  If we quit the app in this case, then
    # *later* attempts to instantiate a napari viewer won't work until
    # the event loop is restarted with app.exec_().  So rather than
    # quit just close all the windows (and clear our app icon).
    else:
        QApplication.setWindowIcon(QIcon())


def run(*, force=False, max_loop_level=1, _func_name="run"):
    """Start the Qt Event Loop

    Parameters
    ----------
    force : bool, optional
        Force the application event_loop to start, even if there are no top
        level widgets to show.
    max_loop_level : int, optional
        The maximum allowable "loop level" for the execution thread.  Every
        time `QApplication.exec_()` is called, Qt enters the event loop,
        increments app.thread().loopLevel(), and waits until exit() is called.
        This function will prevent calling `exec_()` if the application already
        has at least ``max_loop_level`` event loops running.  By default, 1.
    _func_name : str, optional
        name of calling function, by default 'run'.  This is only here to
        provide functions like `gui_qt` a way to inject their name into the
        warning message.

    Raises
    ------
    RuntimeError
        (To avoid confusion) if no widgets would be shown upon starting the
        event loop.
    """
    if _ipython_has_eventloop():
        # If %gui qt is active, we don't need to block again.
        return

    app = QApplication.instance()
    if _pycharm_has_eventloop(app):
        # explicit check for PyCharm pydev console
        return

    if not app:
        raise RuntimeError(
            "No Qt app has been created. One can be created by calling `get_app()` or `qtpy.QtWidgets.QApplication([])`"
        )
    if not app.topLevelWidgets() and not force:
        warn(
            f"Refusing to run a QApplication with no topLevelWidgets. To run the app anyway, use `{_func_name}"
            "(force=True)`",
        )
        return

    if app.thread().loopLevel() >= max_loop_level:
        loops = app.thread().loopLevel()
        warn(
            f"A QApplication is already running with 1 event loop. To enter *another* event loop, use `{_func_name}"
            f"(max_loop_level={max_loop_level})` A QApplication is already running with {loops} event loops. To enter"
            f" *another* event loop, use `{_func_name}(max_loop_level={max_loop_level})`",
        )
        return
    with _maybe_allow_interrupt(app):
        app.exec_()
