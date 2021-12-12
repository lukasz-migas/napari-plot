"""Native window."""
import time
import typing as ty
from functools import partial

from napari._qt.dialogs.screenshot_dialog import ScreenshotDialog
from napari._qt.qt_main_window import _QtMainWindow as Napari_QtMainWindow
from napari._qt.utils import QImg2array
from napari._qt.widgets.qt_viewer_dock_widget import QtViewerDockWidget
from qtpy.QtCore import QEvent, QEventLoop
from qtpy.QtGui import QKeySequence, Qt
from qtpy.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QShortcut,
    QWidget,
)

from ..components.camera import CameraMode, ExtentMode
from ..components.dragtool import DragMode
from ..resources import get_stylesheet
from . import helpers as hp
from .qt_event_loop import get_app, quit_app
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
        # self.setWindowIcon(QIcon(self._window_icon))
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setUnifiedTitleAndToolBarOnMac(True)
        center = QWidget(self)
        center.setLayout(QHBoxLayout())
        center.layout().addWidget(qt_viewer)
        center.layout().setContentsMargins(4, 0, 4, 0)
        self.setCentralWidget(center)
        self.setWindowTitle(qt_viewer.viewer.title)
        _QtMainWindow._instances.append(self)

        # this is required to notifications
        Napari_QtMainWindow._instances.append(self)

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


class Window:
    """Application window that contains the menu bar and viewer.

    Parameters
    ----------
    viewer : napari_1d.components.ViewerModel
        Contained viewer widget.

    Attributes
    ----------
    file_menu : qtpy.QtWidgets.QMenu
        File menu.
    help_menu : qtpy.QtWidgets.QMenu
        Help menu.
    main_menu : qtpy.QtWidgets.QMainWindow.menuBar
        Main menubar.
    qt_viewer : QtViewer
        Contained viewer widget.
    view_menu : qtpy.QtWidgets.QMenu
        View menu.
    window_menu : qtpy.QtWidgets.QMenu
        Window menu.
    """

    def __init__(self, viewer, *, show: bool = True):
        # create QApplication if it doesn't already exist
        get_app()

        # Connect the Viewer and create the Main Window
        self.qt_viewer = QtViewer(viewer, dock_controls=True, add_toolbars=False, disable_controls=True)
        self._qt_window = _QtMainWindow(self.qt_viewer)
        self._status_bar = self._qt_window.statusBar()

        # since we initialize canvas before window, we need to manually connect them again.
        if self._qt_window.windowHandle() is not None:
            self._qt_window.windowHandle().screenChanged.connect(self.qt_viewer.canvas._backend.screen_changed)

        self._add_menubar()
        self._add_file_menu()
        self._add_view_menu()
        self._add_interaction_menu()
        self._add_window_menu()
        self._update_theme()

        self._add_viewer_dock_widget(self.qt_viewer.dockLayerControls, tabify=False)
        self._add_viewer_dock_widget(self.qt_viewer.dockLayerList, tabify=False)

        self._status_bar.showMessage("Ready")
        self._help = QLabel("")
        self._status_bar.addPermanentWidget(self._help)

        viewer.events.status.connect(self._status_changed)
        viewer.events.help.connect(self._help_changed)
        viewer.events.title.connect(self._title_changed)
        viewer.events.theme.connect(self._update_theme)

        if show:
            self.show()

    def _add_viewer_dock_widget(self, dock_widget: QtViewerDockWidget, tabify=False):
        """Add a QtViewerDockWidget to the main window

        If other widgets already present in area then will tabify.

        Parameters
        ----------
        dock_widget : QtViewerDockWidget
            `dock_widget` will be added to the main window.
        tabify : bool
            Flag to tabify dockwidget or not.
        """
        # Find if any othe dock widgets are currently in area
        current_dws_in_area = [
            dw
            for dw in self._qt_window.findChildren(QDockWidget)
            if self._qt_window.dockWidgetArea(dw) == dock_widget.qt_area
        ]
        self._qt_window.addDockWidget(dock_widget.qt_area, dock_widget)

        # If another dock widget present in area then tabify
        if current_dws_in_area:
            if tabify:
                self._qt_window.tabifyDockWidget(current_dws_in_area[-1], dock_widget)
                dock_widget.show()
                dock_widget.raise_()
            elif dock_widget.area in ("right", "left"):
                _wdg = current_dws_in_area + [dock_widget]
                # add sizes to push lower widgets up
                sizes = list(range(1, len(_wdg) * 4, 4))
                self._qt_window.resizeDocks(_wdg, sizes, Qt.Vertical)

        action = dock_widget.toggleViewAction()
        action.setStatusTip(dock_widget.name)
        action.setText(dock_widget.name)
        self.window_menu.addAction(action)

    def _add_menubar(self):
        """Add menubar to napari app."""
        self.main_menu = self._qt_window.menuBar()
        # Menubar shortcuts are only active when the menubar is visible.
        # Therefore, we set a global shortcut not associated with the menubar
        # to toggle visibility, *but*, in order to not shadow the menubar
        # shortcut, we disable it, and only enable it when the menubar is
        # hidden. See this stackoverflow link for details:
        # https://stackoverflow.com/questions/50537642/how-to-keep-the-shortcuts-of-a-hidden-widget-in-pyqt5
        self._main_menu_shortcut = QShortcut(QKeySequence("Ctrl+M"), self._qt_window)
        self._main_menu_shortcut.activated.connect(self._toggle_menubar_visible)
        self._main_menu_shortcut.setEnabled(False)

    def _add_file_menu(self):
        """Add `File` menu to app menubar."""
        screenshot = QAction("Save Screenshot...", self._qt_window)
        screenshot.setShortcut("Alt+S")
        screenshot.setStatusTip("Save screenshot of current display, default .png")
        screenshot.triggered.connect(self.qt_viewer._screenshot_dialog)

        screenshot_wv = QAction("Save Screenshot with Viewer...", self._qt_window)
        screenshot_wv.setShortcut("Alt+Shift+S")
        screenshot_wv.setStatusTip("Save screenshot of current display with the viewer, default .png")
        screenshot_wv.triggered.connect(self._screenshot_dialog)

        clipboard = QAction("Copy Screenshot to Clipboard", self._qt_window)
        clipboard.setStatusTip("Copy screenshot of current display to the clipboard")
        clipboard.triggered.connect(lambda: self.qt_viewer.clipboard())

        clipboard_wv = QAction(
            "Copy Screenshot with Viewer to Clipboard",
            self._qt_window,
        )
        clipboard_wv.setStatusTip("Copy screenshot of current display with the viewer to the clipboard")
        clipboard_wv.triggered.connect(lambda: self.clipboard())

        # OS X will rename this to Quit and put it in the app menu.
        # This quits the entire QApplication and all windows that may be open.
        quitAction = QAction("Exit", self._qt_window)
        quitAction.setShortcut("Ctrl+Q")
        quitAction.setMenuRole(QAction.QuitRole)
        quitAction.triggered.connect(lambda: self._qt_window.close(quit_app=True))

        closeAction = QAction("Close Window", self._qt_window)
        closeAction.setShortcut("Ctrl+W")
        closeAction.triggered.connect(self._qt_window.close_window)

        self.file_menu = self.main_menu.addMenu("&File")
        self.file_menu.addAction(screenshot)
        self.file_menu.addAction(screenshot_wv)
        self.file_menu.addAction(clipboard)
        self.file_menu.addAction(clipboard_wv)
        self.file_menu.addSeparator()
        self.file_menu.addAction(closeAction)
        self.file_menu.addAction(quitAction)

    def _add_view_menu(self):
        """Add 'View' menu to app menubar."""
        toggle_visible = QAction("Toggle Menubar Visibility", self._qt_window)
        toggle_visible.setShortcut("Ctrl+M")
        toggle_visible.setStatusTip("Hide Menubar")
        toggle_visible.triggered.connect(self._toggle_menubar_visible)
        toggle_fullscreen = QAction("Toggle Full Screen", self._qt_window)
        toggle_fullscreen.setShortcut("Ctrl+F")
        toggle_fullscreen.setStatusTip("Toggle full screen")
        toggle_fullscreen.triggered.connect(self._toggle_fullscreen)

        self.view_menu = self.main_menu.addMenu("&View")
        self.view_menu.addAction(toggle_fullscreen)
        self.view_menu.addAction(toggle_visible)
        self.view_menu.addSeparator()

    def _add_interaction_menu(self):
        """Add 'View' menu to app menubar."""
        # add DragMode
        actions = []
        self.view_tools = self.main_menu.addMenu("&Interaction")
        toggle_tool = QAction("Tool: Auto", self._qt_window)
        toggle_tool.setCheckable(True)
        toggle_tool.triggered.connect(lambda: setattr(self.qt_viewer.viewer.drag_tool, "active", DragMode.AUTO))
        toggle_tool.setChecked(True)
        actions.append(toggle_tool)

        self.view_tools.addAction(toggle_tool)
        toggle_tool = QAction("Tool: Box", self._qt_window)
        toggle_tool.setCheckable(True)
        toggle_tool.triggered.connect(lambda: setattr(self.qt_viewer.viewer.drag_tool, "active", DragMode.BOX))
        self.view_tools.addAction(toggle_tool)
        actions.append(toggle_tool)

        toggle_tool = QAction("Tool: Horizontal span", self._qt_window)
        toggle_tool.setCheckable(True)
        toggle_tool.triggered.connect(
            lambda: setattr(self.qt_viewer.viewer.drag_tool, "active", DragMode.HORIZONTAL_SPAN)
        )
        self.view_tools.addAction(toggle_tool)
        actions.append(toggle_tool)

        toggle_tool = QAction("Tool: Vertical span", self._qt_window)
        toggle_tool.setCheckable(True)
        toggle_tool.triggered.connect(
            lambda: setattr(self.qt_viewer.viewer.drag_tool, "active", DragMode.VERTICAL_SPAN)
        )
        self.view_tools.addAction(toggle_tool)
        actions.append(toggle_tool)

        # ensures that only single tool can be selected at at ime
        hp.make_menu_group(self._qt_window, *actions)

        # add CameraMode
        self.view_tools.addSeparator()
        self._menu_camera_all = QAction("Camera mode: No locking", self._qt_window)
        self._menu_camera_all.triggered.connect(partial(self._set_camera_mode, which=CameraMode.ALL))
        self.view_tools.addAction(self._menu_camera_all)

        self._menu_camera_bottom = QAction("Camera mode: Lock to bottom", self._qt_window)
        self._menu_camera_bottom.setCheckable(True)
        self._menu_camera_bottom.triggered.connect(partial(self._set_camera_mode, which=CameraMode.LOCK_TO_BOTTOM))
        # self._menu_camera_bottom.triggered.connect(self._set_camera_mode)
        self.view_tools.addAction(self._menu_camera_bottom)

        self._menu_camera_top = QAction("Camera mode: Lock to top", self._qt_window)
        self._menu_camera_top.setCheckable(True)
        self._menu_camera_top.triggered.connect(partial(self._set_camera_mode, which=CameraMode.LOCK_TO_TOP))
        # self._menu_camera_top.triggered.connect(self._set_camera_mode)
        self.view_tools.addAction(self._menu_camera_top)

        self._menu_camera_left = QAction("Camera mode: Lock to left", self._qt_window)
        self._menu_camera_left.setCheckable(True)
        self._menu_camera_left.triggered.connect(partial(self._set_camera_mode, which=CameraMode.LOCK_TO_LEFT))
        # self._menu_camera_left.triggered.connect(self._set_camera_mode)
        self.view_tools.addAction(self._menu_camera_left)

        self._menu_camera_right = QAction("Camera mode: Lock to right", self._qt_window)
        self._menu_camera_right.setCheckable(True)
        self._menu_camera_right.triggered.connect(partial(self._set_camera_mode, which=CameraMode.LOCK_TO_RIGHT))
        # self._menu_camera_right.triggered.connect(self._set_camera_mode)
        self.view_tools.addAction(self._menu_camera_right)

        # add ExtentMode
        self.view_tools.addSeparator()
        actions = []
        toggle_tool = QAction("Extent mode: Unrestricted", self._qt_window)
        toggle_tool.setCheckable(True)
        toggle_tool.triggered.connect(
            lambda: setattr(self.qt_viewer.viewer.camera, "extent_mode", ExtentMode.UNRESTRICTED)
        )
        self.view_tools.addAction(toggle_tool)
        actions.append(toggle_tool)

        toggle_tool = QAction("Extent mode: Restricted", self._qt_window)
        toggle_tool.setCheckable(True)
        toggle_tool.triggered.connect(
            lambda: setattr(self.qt_viewer.viewer.camera, "extent_mode", ExtentMode.RESTRICTED)
        )
        toggle_tool.setChecked(True)
        self.view_tools.addAction(toggle_tool)
        actions.append(toggle_tool)

        # ensures that only single tool can be selected at at ime
        hp.make_menu_group(self._qt_window, *actions)

    def _add_window_menu(self):
        """Add 'Window' menu to app menubar."""
        self.window_menu = self.main_menu.addMenu("&Window")

    # def _add_help_menu(self):
    #     """Add 'Help' menu to app menubar."""
    #     self.help_menu = self.main_menu.addMenu('&Help')
    #
    #     about_action = QAction("napari-1d Info", self._qt_window)
    #     about_action.setShortcut("Ctrl+/")
    #     about_action.setStatusTip('About napari-1d')
    #     about_action.triggered.connect(
    #         lambda e: QtAbout.showAbout(self.qt_viewer, self._qt_window)
    #     )
    #     self.help_menu.addAction(about_action)

    def _set_camera_mode(self, which: CameraMode):
        """Set camera mode.

        This function wil either rest the `axis_mode` to `ALL` if the `which` reflects that, or update the selection
        of currently checked options.

        Parameters
        ----------
        which : CameraMode
            Which of the menu options was triggered.
        """
        if which == CameraMode.ALL:
            self.qt_viewer.viewer.camera.axis_mode = (CameraMode.ALL,)
            for wdg in [
                self._menu_camera_top,
                self._menu_camera_bottom,
                self._menu_camera_left,
                self._menu_camera_right,
            ]:
                with hp.qt_signals_blocked(wdg):
                    wdg.setChecked(False)
        else:
            camera_modes = []
            if self._menu_camera_top.isChecked():
                camera_modes.append(CameraMode.LOCK_TO_TOP)
            if self._menu_camera_bottom.isChecked():
                camera_modes.append(CameraMode.LOCK_TO_BOTTOM)
            if self._menu_camera_left.isChecked():
                camera_modes.append(CameraMode.LOCK_TO_LEFT)
            if self._menu_camera_right.isChecked():
                camera_modes.append(CameraMode.LOCK_TO_RIGHT)
            self.qt_viewer.viewer.camera.axis_mode = tuple(camera_modes)

    def _toggle_menubar_visible(self):
        """Toggle visibility of app menubar.

        This function also disables or enables a global keyboard shortcut to
        show the menubar, since menubar shortcuts are only available while the
        menubar is visible.
        """
        if self.main_menu.isVisible():
            self.main_menu.setVisible(False)
            self._main_menu_shortcut.setEnabled(True)
        else:
            self.main_menu.setVisible(True)
            self._main_menu_shortcut.setEnabled(False)

    def _toggle_fullscreen(self, event):
        """Toggle fullscreen mode."""
        if self._qt_window.isFullScreen():
            self._qt_window.showNormal()
        else:
            self._qt_window.showFullScreen()

    def _update_theme(self, event=None):
        """Update widget color theme."""
        try:
            if event:
                value = event.value
                self.qt_viewer.viewer.theme = value
            else:
                value = self.qt_viewer.viewer.theme

            self._qt_window.setStyleSheet(get_stylesheet(value))
        except (AttributeError, RuntimeError):  # wrapped C/C++ object may have been deleted
            pass

    def _status_changed(self, event):
        """Update status bar.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        self._status_bar.showMessage(event.value)

    def _title_changed(self, event):
        """Update window title.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        self._qt_window.setWindowTitle(event.value)

    def _help_changed(self, event):
        """Update help message on status bar.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        self._help.setText(event.value)

    def close(self):
        """Close the viewer window and cleanup sub-widgets."""
        # Someone is closing us twice? Only try to delete self._qt_window
        # if we still have one.
        if hasattr(self, "_qt_window"):
            self.qt_viewer.close()
            self._qt_window.close()
            del self._qt_window

    def resize(self, width, height):
        """Resize the window.

        Parameters
        ----------
        width : int
            Width in logical pixels.
        height : int
            Height in logical pixels.
        """
        self._qt_window.resize(width, height)

    def show(self, *, block=False):
        """Resize, show, and bring forward the window.

        Raises
        ------
        RuntimeError
            If the viewer.window has already been closed and deleted.
        """
        try:
            self._qt_window.show(block=block)
        except (AttributeError, RuntimeError):
            raise RuntimeError(
                "This viewer has already been closed and deleted. Please create a new one.",
            )

        # We want to bring the viewer to the front when
        # A) it is our own event loop OR we are running in jupyter
        # B) it is not the first time a QMainWindow is being created
        app_name = QApplication.instance().applicationName()
        if app_name == "napari-1d":
            self.activate()

    def activate(self):
        """Make the viewer the currently active window."""
        self._qt_window.raise_()  # for macOS
        self._qt_window.activateWindow()  # for Windows

    def _screenshot_dialog(self):
        """Save screenshot of current display with viewer, default .png"""
        dial = ScreenshotDialog(self.screenshot, self.qt_viewer)

        if dial.exec_():
            pass
            # dial.selectedFiles()[0]

    def _screenshot(self, flash=True):
        """Capture screenshot of the currently displayed viewer.

        Parameters
        ----------
        flash : bool
            Flag to indicate whether flash animation should be shown after
            the screenshot was captured.
        """
        img = self._qt_window.grab().toImage()
        if flash:
            from napari._qt.utils import add_flash_animation

            add_flash_animation(self._qt_window)
        return img

    def screenshot(self, path=None, flash=True):
        """Take currently displayed viewer and convert to an image array.

        Parameters
        ----------
        path : str
            Filename for saving screenshot image.
        flash : bool
            Flag to indicate whether flash animation should be shown after
            the screenshot was captured.

        Returns
        -------
        image : array
            Numpy array of type ubyte and shape (h, w, 4). Index [0, 0] is the
            upper-left corner of the rendered region.
        """
        from napari.utils.io import imsave

        img = self._screenshot(flash)
        if path is not None:
            imsave(path, QImg2array(img))  # scikit-image imsave method
        return QImg2array(img)

    def clipboard(self, flash=True):
        """Take a screenshot of the currently displayed viewer and copy the image to the clipboard.

        Parameters
        ----------
        flash : bool
            Flag to indicate whether flash animation should be shown after
            the screenshot was captured.
        """
        from qtpy.QtGui import QGuiApplication

        img = self._screenshot(flash)
        cb = QGuiApplication.clipboard()
        cb.setImage(img)
