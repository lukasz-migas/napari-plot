"""Native window."""

from __future__ import annotations

import contextlib
import logging
import os
import sys
import time
import typing as ty
from functools import partial
from pathlib import Path
from weakref import WeakValueDictionary

import numpy as np
import qtextra.helpers as hp
from napari._qt._qapp_model.qactions import add_dummy_actions, init_qactions
from napari._qt._qapp_model.qactions._debug import _is_set_trace_active
from napari._qt.dialogs.confirm_close_dialog import ConfirmCloseDialog
from napari._qt.dialogs.qt_activity_dialog import QtActivityDialog
from napari._qt.dialogs.qt_notification import NapariQtNotification
from napari._qt.dialogs.screenshot_dialog import ScreenshotDialog
from napari._qt.qt_main_window import _QtMainWindow as Napari_QtMainWindow
from napari._qt.threads.status_checker import StatusChecker
from napari._qt.utils import QImg2array
from napari._qt.widgets.qt_viewer_dock_widget import QtViewerDockWidget
from napari._qt.widgets.qt_viewer_status_bar import ViewerStatusBar
from napari.settings import get_settings
from napari.utils.events import Event
from napari.utils.misc import in_jupyter, running_as_constructor_app
from napari.utils.notifications import Notification
from qtpy.QtCore import QEvent, QEventLoop, QPoint, QProcess, QRect, Qt, Slot
from qtpy.QtGui import QHideEvent, QIcon, QImage, QKeySequence, QShowEvent
from qtpy.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QDockWidget,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QShortcut,
    QToolTip,
    QWidget,
)

from napari_plot._app_model.context import create_context
from napari_plot._qt.qt_event_loop import NAPARI_PLOT_ICON_PATH, get_app, quit_app
from napari_plot._qt.qt_viewer import QtViewer
from napari_plot.components.camera import CameraMode, ExtentMode
from napari_plot.components.dragtool import DragMode
from napari_plot.resources import get_stylesheet

if ty.TYPE_CHECKING:
    from magicgui.widgets import Widget

    from napari_plot.viewer import Viewer

logger = logging.getLogger()

_sentinel = object()


class _QtMainWindow(QMainWindow):
    """Main window."""

    # This was added so that someone can patch
    # `napari._qt.qt_main_window._QtMainWindow._window_icon`
    # to their desired window icon
    _window_icon = NAPARI_PLOT_ICON_PATH

    # To track window instances and facilitate getting the "active" viewer...
    # We use this instead of QApplication.activeWindow for compatibility with
    # IPython usage. When you activate IPython, it will appear that there are
    # *no* active windows, so we want to track the most recently active windows
    _instances: ty.ClassVar[ty.List[_QtMainWindow]] = []

    def __init__(self, viewer: Viewer, window: Window, parent=None) -> None:
        super().__init__(parent)
        self._ev = None
        self._window = window
        self._qt_viewer = QtViewer(
            viewer,
            dock_controls=True,
            add_toolbars=False,
            disable_controls=True,
            dock_console=True,
            dock_axis=True,
            dock_camera=True,
            show_welcome_screen=True,
        )
        self._quit_app = False
        self.setWindowIcon(QIcon(self._window_icon))
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        center = QWidget(self)
        center.setLayout(QHBoxLayout())
        center.layout().addWidget(self._qt_viewer)
        center.layout().setContentsMargins(4, 0, 4, 0)
        self.setCentralWidget(center)
        self.setWindowTitle(self._qt_viewer.viewer.title)

        self._maximized_flag = False
        self._normal_geometry = QRect()
        self._window_size = None
        self._window_pos = None
        self._old_size = None
        self._positions = []
        self._toggle_menubar_visibility = False
        # QtReload widget for development purposes.
        self._qdev = None
        self._dockQDev = None

        # this ia sa workaround for #5335 issue. The dict is used to not
        # collide shortcuts for close and close all windows
        self._is_close_dialog = {False: True, True: True}

        act_dlg = QtActivityDialog(self._qt_viewer._welcome_widget)
        self._qt_viewer._welcome_widget.resized.connect(act_dlg.move_to_bottom_right)
        act_dlg.hide()
        self._activity_dialog = act_dlg

        self.setStatusBar(ViewerStatusBar(self))

        # Prevent QLineEdit based widgets to keep focus even when clicks are
        # done outside the widget. See #1571
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Ideally this would be in `NapariApplication` but that is outside of Qt
        self._viewer_context = create_context(self)
        self._viewer_context["is_set_trace_active"] = _is_set_trace_active

        # since we initialize canvas before window,
        # we need to manually connect them again.
        handle = self.windowHandle()
        if handle is not None:
            handle.screenChanged.connect(self._qt_viewer.canvas.screen_changed)

        # this is the line that initializes any Qt-based app-model Actions that
        # were defined somewhere in the `_qt` module and imported in init_qactions
        init_qactions()

        with contextlib.suppress(IndexError):
            viewer.cursor.events.position.disconnect(viewer.update_status_from_cursor)

        self.status_thread = StatusChecker(viewer, parent=self)
        self.status_thread.status_and_tooltip_changed.connect(self.set_status_and_tooltip)
        viewer.cursor.events.position.connect(self.status_thread.trigger_status_update)

        # Keep track of current instance
        _QtMainWindow._instances.append(self)
        # This is required for notifications to work properly
        Napari_QtMainWindow._instances.append(self)

    def _toggle_status_thread(self, event: Event):
        if event.value:
            self.status_thread.start()
        else:
            self.status_thread.terminate()

    def showEvent(self, event: QShowEvent):
        """Override to handle window state changes."""
        settings = get_settings()
        # if event loop is not running, we don't want to start the thread
        # If event loop is running, the loopLevel will be above 0
        if settings.appearance.update_status_based_on_layer and QApplication.instance().thread().loopLevel():
            self.status_thread.start()
        super().showEvent(event)

    def enterEvent(self, a0):
        # as we call show in Viewer constructor, we need to start the thread
        # when the mouse enters the window
        # as first call of showEvent is before the event loop is running
        if get_settings().appearance.update_status_based_on_layer and not self.status_thread.isRunning():
            self.status_thread.start()
        super().enterEvent(a0)

    def hideEvent(self, event: QHideEvent):
        self.status_thread.terminate()
        super().hideEvent(event)

    def set_status_and_tooltip(self, status_and_tooltip: ty.Optional[tuple[ty.Union[str, dict], str]]):
        if status_and_tooltip is None:
            return
        self._qt_viewer.viewer.status = status_and_tooltip[0]
        self._qt_viewer.viewer.tooltip.text = status_and_tooltip[1]
        if (active := self._qt_viewer.viewer.layers.selection.active) is not None:
            self._qt_viewer.viewer.help = active.help

    def statusBar(self) -> ViewerStatusBar:
        """Return statusbar."""
        return super().statusBar()

    @classmethod
    def current(cls):
        """Return current window instance."""
        return cls._instances[-1] if cls._instances else None

    @classmethod
    def current_viewer(cls):
        """Return current viewer instance."""
        window = cls.current()
        return window._qt_viewer.viewer if window else None

    def event(self, e: QEvent) -> bool:
        """Override Qt method."""
        if e.type() == QEvent.Type.ToolTip and self._qt_viewer.viewer.tooltip.visible:
            # globalPos is for Qt5 e.globalPosition().toPoint() is for QT6
            # https://doc-snapshots.qt.io/qt6-dev/qmouseevent-obsolete.html#globalPos
            pnt = e.globalPosition().toPoint() if hasattr(e, "globalPosition") else e.globalPos()
            QToolTip.showText(pnt, self._qt_viewer.viewer.tooltip.text, self)
        if e.type() in {QEvent.Type.WindowActivate, QEvent.Type.ZOrderChange}:
            # upon activation or raise_, put window at the end of _instances
            with contextlib.suppress(ValueError):
                inst = _QtMainWindow._instances
                inst.append(inst.pop(inst.index(self)))
        if e.type() == QEvent.Type.Close:
            # when we close the MainWindow, remove it from the instances list
            with contextlib.suppress(ValueError):
                _QtMainWindow._instances.remove(self)
        return super().event(e)

    def showFullScreen(self):
        super().showFullScreen()
        # Handle OpenGL based windows fullscreen issue on Windows.
        # For more info see:
        #  * https://doc.qt.io/qt-6/windows-issues.html#fullscreen-opengl-based-windows
        #  * https://bugreports.qt.io/browse/QTBUG-41309
        #  * https://bugreports.qt.io/browse/QTBUG-104511
        if os.name != "nt":
            return
        import win32con
        import win32gui

        if self.windowHandle():
            handle = int(self.windowHandle().winId())
            win32gui.SetWindowLong(
                handle,
                win32con.GWL_STYLE,
                win32gui.GetWindowLong(handle, win32con.GWL_STYLE) | win32con.WS_BORDER,
            )

    def eventFilter(self, source, event):
        """Event filter."""
        # Handle showing hidden menubar on mouse move event.
        # We do not hide menubar when a menu is being shown or
        # we are not in menubar toggled state
        if (
            QApplication.activePopupWidget() is None
            and hasattr(self, "_toggle_menubar_visibility")
            and self._toggle_menubar_visibility
        ):
            if event.type() == QEvent.MouseMove:
                if self.menuBar().isHidden():
                    rect = self.geometry()
                    # set mouse-sensitive zone to trigger showing the menubar
                    rect.setHeight(25)
                    if rect.contains(event.globalPos()):
                        self.menuBar().show()
                else:
                    rect = QRect(
                        self.menuBar().mapToGlobal(QPoint(0, 0)),
                        self.menuBar().size(),
                    )
                    if not rect.contains(event.globalPos()):
                        self.menuBar().hide()
            elif event.type() == QEvent.Leave and source is self:
                self.menuBar().hide()
        return QMainWindow.eventFilter(self, source, event)

    def close(self, quit_app=False, confirm_need=False):
        """Override to handle closing app or just the window."""
        if not quit_app and not self._qt_viewer.viewer.layers:
            return super().close()
        confirm_need_local = confirm_need and self._is_close_dialog[quit_app]
        self._is_close_dialog[quit_app] = False
        # here we save information that we could request confirmation on close
        # So fi function `close` is called again, we don't ask again but just close
        if (
            not confirm_need_local
            # or not get_settings().application.confirm_close_window
            or ConfirmCloseDialog(self, quit_app).exec_() == QDialog.DialogCode.Accepted
        ):
            self._quit_app = quit_app
            self._is_close_dialog[quit_app] = True
            # here we inform that confirmation dialog is not open
            self._qt_viewer.dims.stop()
            return super().close()
        # here we inform that confirmation dialog is not open
        self._is_close_dialog[quit_app] = True
        return None

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
            except AttributeError:
                parent = getattr(parent, "_parent", None)

    def show(self, block=False):
        """Show window."""
        super().show()
        self._qt_viewer.setFocus()
        if block:
            self._ev = QEventLoop()
            self._ev.exec()

    def changeEvent(self, event):
        """Handle window state changes."""
        if event.type() == QEvent.Type.WindowStateChange:
            # TODO: handle maximization issue. When double clicking on the
            # title bar on Mac the resizeEvent is called an varying amount
            # of times which makes it hard to track the original size before
            # maximization.
            condition = self.isMaximized() if os.name == "nt" else self.isFullScreen()
            if condition and self._old_size is not None:
                if self._positions and len(self._positions) > 1:
                    self._window_pos = self._positions[-2]

                self._window_size = (
                    self._old_size.width(),
                    self._old_size.height(),
                )
            else:
                self._old_size = None
                self._window_pos = None
                self._window_size = None
                self._positions = []

        super().changeEvent(event)

    def keyPressEvent(self, event):
        """Called whenever a key is pressed.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self._qt_viewer.canvas._scene_canvas._backend._keyEvent(
            self._qt_viewer.canvas._scene_canvas.events.key_press, event
        )
        event.accept()

    def keyReleaseEvent(self, event):
        """Called whenever a key is released.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self._qt_viewer.canvas._scene_canvas._backend._keyEvent(
            self._qt_viewer.canvas._scene_canvas.events.key_release, event
        )
        event.accept()

    def resizeEvent(self, event):
        """Override to handle original size before maximizing."""
        # the first resize event will have nonsense positions that we don't
        # want to store (and potentially restore)
        if event.oldSize().isValid():
            self._old_size = event.oldSize()
            self._positions.append((self.x(), self.y()))

            if self._positions and len(self._positions) >= 2:
                self._window_pos = self._positions[-2]
                self._positions = self._positions[-2:]

        super().resizeEvent(event)

    def closeEvent(self, event):
        """This method will be called when the main window is closing.

        Regardless of whether cmd Q, cmd W, or the close button is used...
        """
        if (
            event.spontaneous()
            and self._qt_viewer.viewer.layers
            and ConfirmCloseDialog(self, False).exec_() != QDialog.DialogCode.Accepted
        ):
            event.ignore()
            return

        if self._ev and self._ev.isRunning():
            self._ev.quit()

        # Close any floating dockwidgets
        for dock in self.findChildren(QtViewerDockWidget):
            if isinstance(dock, QWidget) and dock.isFloating():
                dock.setFloating(False)

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

    def restart(self):
        """Restart the napari application in a detached process."""
        process = QProcess()
        process.setProgram(sys.executable)

        if not running_as_constructor_app():
            process.setArguments(sys.argv)

        process.startDetached()
        self.close(quit_app=True)

    def toggle_menubar_visibility(self):
        """
        Change menubar to be shown or to be hidden and shown on mouse movement.

        For the mouse movement functionality see the `eventFilter` implementation.
        """
        self._toggle_menubar_visibility = not self._toggle_menubar_visibility
        self.menuBar().setVisible(not self._toggle_menubar_visibility)
        return self._toggle_menubar_visibility

    @staticmethod
    @Slot(Notification)
    def show_notification(notification: Notification):
        """Show notification coming from a thread."""
        NapariQtNotification.show_notification(notification)


class Window:
    """Application window that contains the menu bar and viewer.

    Parameters
    ----------
    viewer : napari_plot.components.ViewerModel
        Contained viewer widget.

    Attributes
    ----------
    file_menu : qtpy.QtWidgets.QMenu
        File menu.
    help_menu : qtpy.QtWidgets.QMenu
        Help menu.
    main_menu : qtpy.QtWidgets.QMainWindow.menuBar
        Main menubar.
    _qt_viewer : QtViewer
        Contained viewer widget.
    view_menu : qtpy.QtWidgets.QMenu
        View menu.
    window_menu : qtpy.QtWidgets.QMenu
        Window menu.
    """

    _dev = None

    def __init__(self, viewer, *, show: bool = True):
        # create QApplication if it doesn't already exist
        qapp = get_app()

        # Dictionary holding dock widgets
        self._dock_widgets: ty.Dict[str, QtViewerDockWidget] = WeakValueDictionary()
        self._unnamed_dockwidget_count = 1

        # Connect the Viewer and create the Main Window
        self._qt_window: QMainWindow = _QtMainWindow(viewer, self)
        qapp.installEventFilter(self._qt_window)

        self._add_menubar()
        self._add_file_menu()
        self._add_view_menu()
        self._add_interaction_menu()
        self._add_window_menu()
        # TODO: the dummy actions should **not** live on the layerlist context
        # as they are unrelated. However, we do not currently have a suitable
        # enclosing context where we could store these keys, such that they
        # **and** the layerlist context key are available when we update
        # menus. We need a single context to contain all keys required for
        # menu update, so we add them to the layerlist context for now.
        add_dummy_actions(self._qt_viewer.viewer.layers._ctx)

        self._update_theme()

        if hasattr(self._qt_viewer, "dockConsole"):
            self._add_viewer_dock_widget(self._qt_viewer.dockConsole, tabify=False, menu=self.window_menu)
        self._add_viewer_dock_widget(self._qt_viewer.dockLayerControls, tabify=False, menu=self.window_menu)
        self._add_viewer_dock_widget(self._qt_viewer.dockLayerList, tabify=False, menu=self.window_menu)
        if hasattr(self._qt_viewer, "dockCamera"):
            self._add_viewer_dock_widget(self._qt_viewer.dockCamera, tabify=False, menu=self.window_menu)
        if hasattr(self._qt_viewer, "dockAxis"):
            self._add_viewer_dock_widget(self._qt_viewer.dockAxis, tabify=False, menu=self.window_menu)

        viewer.events.help.connect(self._help_changed)
        viewer.events.title.connect(self._title_changed)
        viewer.events.theme.connect(self._update_theme)
        viewer.events.status.connect(self._status_changed)

        # Setup development tools
        self._create_dev_tools()

        if show:
            self.show()
            # Ensure the controls dock uses the minimum height
            self._qt_window.resizeDocks(
                [
                    self._qt_viewer.dockLayerControls,
                    self._qt_viewer.dockLayerList,
                ],
                [self._qt_viewer.dockLayerControls.minimumHeight(), 10000],
                Qt.Orientation.Vertical,
            )

    def _create_dev_tools(self):
        """Setup development tools."""
        try:
            if os.getenv("NAPARI_PLOT_DEV", "0") == "1" and self._dev is None:
                from napari_plot._qt.widgets.qt_dev import install_debugger_hook, qdev

                logging.getLogger("napari_plot").setLevel(logging.DEBUG)
                self._qdev = qdev()
                self._dockQDev = QtViewerDockWidget(
                    self,
                    self._qdev,
                    name="hot reload",
                    area="bottom",
                    allowed_areas=["left", "right", "bottom"],
                    object_name="QDev",
                    close_btn=False,
                )
                self._add_viewer_dock_widget(self._dockQDev, tabify=False, menu=self.window_menu)
                install_debugger_hook()
        except Exception as e:  # noqa
            pass

    @property
    def _qt_viewer(self):
        # this is starting to be "vestigial"... this property could be removed
        return self._qt_window._qt_viewer

    @property
    def _status_bar(self):
        # TODO: remove from window
        return self._qt_window.statusBar()

    def add_dock_widget(
        self,
        widget: ty.Union[QWidget, Widget],
        *,
        name: str = "",
        area: ty.Optional[str] = None,
        allowed_areas: ty.Optional[ty.Sequence[str]] = None,
        add_vertical_stretch=True,
        tabify: bool = False,
        menu: ty.Optional[QMenu] = None,
    ):
        """Convenience method to add a QDockWidget to the main window.

        If name is not provided a generic name will be addded to avoid
        `saveState` warnings on close.

        Parameters
        ----------
        widget : QWidget
            `widget` will be added as QDockWidget's main widget.
        name : str, optional
            Name of dock widget to appear in window menu.
        area : str
            Side of the main window to which the new dock widget will be added.
            Must be in {'left', 'right', 'top', 'bottom'}
        allowed_areas : list[str], optional
            Areas, relative to the main window, that the widget is allowed dock.
            Each item in list must be in {'left', 'right', 'top', 'bottom'}
            By default, all areas are allowed.
        shortcut : str, optional
            Keyboard shortcut to appear in dropdown menu.
        add_vertical_stretch : bool, optional
            Whether to add stretch to the bottom of vertical widgets (pushing
            widgets up towards the top of the allotted area, instead of letting
            them distribute across the vertical space).  By default, True.

            .. deprecated:: 0.4.8

                The shortcut parameter is deprecated since version 0.4.8, please use
                the action and shortcut manager APIs. The new action manager and
                shortcut API allow user configuration and localization.
        tabify : bool
            Flag to tabify dock widget or not.
        menu : QMenu, optional
            Menu bar to add toggle action to. If `None` nothing added to menu.

        Returns
        -------
        dock_widget : QtViewerDockWidget
            `dock_widget` that can pass viewer events.
        """
        if not name:
            with contextlib.suppress(AttributeError):
                name = widget.objectName()
            name = name or f"Dock widget {self._unnamed_dockwidget_count}"

            self._unnamed_dockwidget_count += 1

        if area is None:
            settings = get_settings()
            area = settings.application.plugin_widget_positions.get(name, "right")

        dock_widget = QtViewerDockWidget(
            self._qt_viewer,
            widget,
            name=name,
            area=area,
            allowed_areas=allowed_areas,
            add_vertical_stretch=add_vertical_stretch,
        )

        self._add_viewer_dock_widget(dock_widget, tabify=tabify, menu=menu)

        if hasattr(widget, "reset_choices"):
            # Keep the dropdown menus in the widget in sync with the layer model
            # if widget has a `reset_choices`, which is true for all magicgui
            # `CategoricalWidget`s
            layers_events = self._qt_viewer.viewer.layers.events
            layers_events.inserted.connect(widget.reset_choices)
            layers_events.removed.connect(widget.reset_choices)
            layers_events.reordered.connect(widget.reset_choices)

        # Add dock widget to dictionary
        self._dock_widgets[dock_widget.name] = dock_widget

        return dock_widget

    def _add_viewer_dock_widget(self, dock_widget: QtViewerDockWidget, tabify=False, menu=None):
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
                self._qt_window.resizeDocks(_wdg, sizes, Qt.Orientation.Vertical)

        if menu:
            action = dock_widget.toggleViewAction()
            action.setStatusTip(dock_widget.name)
            action.setText(dock_widget.name)
            menu.addAction(action)

        # see #3663, to fix #3624 more generally
        dock_widget.setFloating(False)

    def _remove_dock_widget(self, event=None):
        names = list(self._dock_widgets.keys())
        for widget_name in names:
            if event.value in widget_name:
                # remove this widget
                widget = self._dock_widgets[widget_name]
                self.remove_dock_widget(widget)

    def remove_dock_widget(self, widget: QWidget, menu=None):
        """Removes specified dock widget.

        If a QDockWidget is not provided, the existing QDockWidgets will be
        searched for one whose inner widget (``.widget()``) is the provided
        ``widget``.

        Parameters
        ----------
        widget : QWidget | str
            If widget == 'all', all docked widgets will be removed.
        """
        if widget == "all":
            for dw in list(self._dock_widgets.values()):
                self.remove_dock_widget(dw)
            return

        if not isinstance(widget, QDockWidget):
            for dw in self._qt_window.findChildren(QDockWidget):
                if dw.widget() is widget:
                    _dw: QDockWidget = dw
                    break
            else:
                raise LookupError(
                    "Could not find a dock widget containing: {widget}",
                )
        else:
            _dw = widget

        if _dw.widget():
            _dw.widget().setParent(None)
        self._qt_window.removeDockWidget(_dw)
        if menu is not None:
            menu.removeAction(_dw.toggleViewAction())

        # Remove dock widget from dictionary
        self._dock_widgets.pop(_dw.name, None)

        # Deleting the dock widget means any references to it will no longer
        # work but it's not really useful anyway, since the inner widget has
        # been removed. and anyway: people should be using add_dock_widget
        # rather than directly using _add_viewer_dock_widget
        _dw.deleteLater()

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
        screenshot.triggered.connect(self._qt_viewer._screenshot_dialog)

        screenshot_wv = QAction("Save Screenshot with Viewer...", self._qt_window)
        screenshot_wv.setShortcut("Alt+Shift+S")
        screenshot_wv.setStatusTip("Save screenshot of current display with the viewer, default .png")
        screenshot_wv.triggered.connect(self._screenshot_dialog)

        clipboard = QAction("Copy Screenshot to Clipboard", self._qt_window)
        clipboard.setStatusTip("Copy screenshot of current display to the clipboard")
        clipboard.triggered.connect(lambda: self._qt_viewer.clipboard())

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

        # Change colors
        toggle_dark = QAction("Use Dark canvas", self._qt_window)
        toggle_dark.setStatusTip("Change background of the canvas to black with white axes.")
        toggle_dark.triggered.connect(partial(self._toggle_background, "dark"))
        toggle_dark.setCheckable(True)
        toggle_dark.setChecked(True)
        toggle_light = QAction("Use Light canvas", self._qt_window)
        toggle_light.setStatusTip("Change background of the canvas to white with black axes.")
        toggle_light.triggered.connect(partial(self._toggle_background, "light"))
        toggle_light.setCheckable(True)

        hp.make_menu_group(self._qt_window, toggle_dark, toggle_light)

        self.view_menu = self.main_menu.addMenu("&View")
        self.view_menu.addAction(toggle_fullscreen)
        self.view_menu.addAction(toggle_visible)
        self.view_menu.addSeparator()
        self.view_menu.addAction(toggle_dark)
        self.view_menu.addAction(toggle_light)

    def _add_interaction_menu(self):
        """Add 'View' menu to app menubar."""
        # add DragMode
        self.view_tools = self.main_menu.addMenu("&Interaction")
        self._menu_tool_auto = QAction("Tool: Auto (zoom)", self._qt_window)
        self._menu_tool_auto.setCheckable(True)
        self._menu_tool_auto.setChecked(True)
        self._menu_tool_auto.triggered.connect(
            lambda: setattr(self._qt_viewer.viewer.drag_tool, "active", DragMode.AUTO)
        )
        self.view_tools.addAction(self._menu_tool_auto)

        self._menu_tool_box = QAction("Tool: Box (zoom)", self._qt_window)
        self._menu_tool_box.setCheckable(True)
        self._menu_tool_box.triggered.connect(lambda: setattr(self._qt_viewer.viewer.drag_tool, "active", DragMode.BOX))
        self.view_tools.addAction(self._menu_tool_box)

        self._menu_tool_h_span = QAction("Tool: Horizontal span (zoom)", self._qt_window)
        self._menu_tool_h_span.setCheckable(True)
        self._menu_tool_h_span.triggered.connect(
            lambda: setattr(self._qt_viewer.viewer.drag_tool, "active", DragMode.HORIZONTAL_SPAN)
        )
        self.view_tools.addAction(self._menu_tool_h_span)

        self._menu_tool_v_span = QAction("Tool: Vertical span (zoom)", self._qt_window)
        self._menu_tool_v_span.setCheckable(True)
        self._menu_tool_v_span.triggered.connect(
            lambda: setattr(self._qt_viewer.viewer.drag_tool, "active", DragMode.VERTICAL_SPAN)
        )
        self.view_tools.addAction(self._menu_tool_v_span)
        self.view_tools.addSeparator()

        self._menu_tool_box_select = QAction("Select tool: Box (select)", self._qt_window)
        self._menu_tool_box_select.setCheckable(True)
        self._menu_tool_box_select.triggered.connect(
            lambda: setattr(self._qt_viewer.viewer.drag_tool, "active", DragMode.BOX_SELECT)
        )
        self.view_tools.addAction(self._menu_tool_box_select)

        self._menu_tool_polygon = QAction("Select tool: Polygon (select)", self._qt_window)
        self._menu_tool_polygon.setCheckable(True)
        self._menu_tool_polygon.triggered.connect(
            lambda: setattr(self._qt_viewer.viewer.drag_tool, "active", DragMode.POLYGON)
        )
        self.view_tools.addAction(self._menu_tool_polygon)

        self._menu_tool_lasso = QAction("Select tool: Lasso (select)", self._qt_window)
        self._menu_tool_lasso.setCheckable(True)
        self._menu_tool_lasso.triggered.connect(
            lambda: setattr(self._qt_viewer.viewer.drag_tool, "active", DragMode.LASSO)
        )
        self.view_tools.addAction(self._menu_tool_lasso)

        # ensures that only single tool can be selected at at ime
        hp.make_menu_group(
            self._qt_window,
            self._menu_tool_auto,
            self._menu_tool_box,
            self._menu_tool_v_span,
            self._menu_tool_h_span,
            self._menu_tool_polygon,
            self._menu_tool_lasso,
            self._menu_tool_box_select,
        )

        # add CameraMode
        self.view_tools.addSeparator()
        self._menu_camera_all = QAction("Camera mode: No locking", self._qt_window)
        self._menu_camera_all.triggered.connect(partial(self._set_camera_mode, which=CameraMode.ALL))
        self.view_tools.addAction(self._menu_camera_all)

        self._menu_camera_top = QAction("Camera mode: Lock to top", self._qt_window)
        self._menu_camera_top.setCheckable(True)
        self._menu_camera_top.triggered.connect(partial(self._set_camera_mode, which=CameraMode.LOCK_TO_TOP))
        self.view_tools.addAction(self._menu_camera_top)

        self._menu_camera_bottom = QAction("Camera mode: Lock to bottom", self._qt_window)
        self._menu_camera_bottom.setCheckable(True)
        self._menu_camera_bottom.triggered.connect(partial(self._set_camera_mode, which=CameraMode.LOCK_TO_BOTTOM))
        self.view_tools.addAction(self._menu_camera_bottom)

        self._menu_camera_left = QAction("Camera mode: Lock to left", self._qt_window)
        self._menu_camera_left.setCheckable(True)
        self._menu_camera_left.triggered.connect(partial(self._set_camera_mode, which=CameraMode.LOCK_TO_LEFT))
        self.view_tools.addAction(self._menu_camera_left)

        self._menu_camera_right = QAction("Camera mode: Lock to right", self._qt_window)
        self._menu_camera_right.setCheckable(True)
        self._menu_camera_right.triggered.connect(partial(self._set_camera_mode, which=CameraMode.LOCK_TO_RIGHT))
        self.view_tools.addAction(self._menu_camera_right)

        # add ExtentMode
        self.view_tools.addSeparator()
        self._menu_extent_unrestricted = QAction("Extent mode: Unrestricted", self._qt_window)
        self._menu_extent_unrestricted.setCheckable(True)
        self._menu_extent_unrestricted.setChecked(True)
        self._menu_extent_unrestricted.triggered.connect(
            lambda: setattr(self._qt_viewer.viewer.camera, "extent_mode", ExtentMode.UNRESTRICTED)
        )
        self.view_tools.addAction(self._menu_extent_unrestricted)

        self._menu_extent_restricted = QAction("Extent mode: Restricted", self._qt_window)
        self._menu_extent_restricted.setCheckable(True)
        self._menu_extent_restricted.triggered.connect(
            lambda: setattr(self._qt_viewer.viewer.camera, "extent_mode", ExtentMode.RESTRICTED)
        )
        self.view_tools.addAction(self._menu_extent_restricted)

        # ensures that only single tool can be selected at at ime
        hp.make_menu_group(
            self._qt_window,
            self._menu_extent_unrestricted,
            self._menu_extent_restricted,
        )

        self._qt_viewer.viewer.drag_tool.events.active.connect(self._on_tool_change)
        self._qt_viewer.viewer.camera.events.extent_mode.connect(self._on_extent_change)
        self._qt_viewer.viewer.camera.events.axis_mode.connect(self._on_axis_mode_change)

    def _add_window_menu(self):
        """Add 'Window' menu to app menubar."""
        self.window_menu = self.main_menu.addMenu("&Window")

    # def _add_help_menu(self):
    #     """Add 'Help' menu to app menubar."""
    #     self.help_menu = self.main_menu.addMenu('&Help')
    #
    #     about_action = QAction("napari-plot Info", self._qt_window)
    #     about_action.setShortcut("Ctrl+/")
    #     about_action.setStatusTip('About napari-plot')
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
            self._qt_viewer.viewer.camera.axis_mode = (CameraMode.ALL,)
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
            self._qt_viewer.viewer.camera.axis_mode = tuple(camera_modes)

    def _on_extent_change(self, event=None):
        """Update menu appropriately."""
        state = self._qt_viewer.viewer.camera.extent_mode
        if state == ExtentMode.RESTRICTED:
            self._menu_extent_restricted.setChecked(True)
        else:
            self._menu_extent_unrestricted.setChecked(True)
        for wdg in [
            self._menu_camera_all,
            self._menu_camera_top,
            self._menu_camera_bottom,
            self._menu_camera_left,
            self._menu_camera_right,
        ]:
            wdg.setDisabled(state == ExtentMode.UNRESTRICTED)

    def _on_tool_change(self, event=None):
        """Update menu appropriately."""
        state = self._qt_viewer.viewer.drag_tool.active
        if state == DragMode.AUTO:
            self._menu_tool_auto.setChecked(True)
        elif state == DragMode.BOX:
            self._menu_tool_box.setChecked(True)
        elif state == DragMode.VERTICAL_SPAN:
            self._menu_tool_v_span.setChecked(True)
        elif state == DragMode.LASSO:
            self._menu_tool_lasso.setChecked(True)
        elif state == DragMode.BOX_SELECT:
            self._menu_tool_box_select.setChecked(True)
        elif state == DragMode.POLYGON:
            self._menu_tool_polygon.setChecked(True)
        else:
            self._menu_tool_h_span.setChecked(True)

    def _on_axis_mode_change(self, event=None):
        """Update camera menu."""
        state = self._qt_viewer.viewer.camera.axis_mode
        if CameraMode.ALL in state:
            for wdg in [
                self._menu_camera_top,
                self._menu_camera_bottom,
                self._menu_camera_left,
                self._menu_camera_right,
            ]:
                with hp.qt_signals_blocked(wdg):
                    wdg.setChecked(False)
        else:
            with hp.qt_signals_blocked(self._menu_camera_top):
                self._menu_camera_top.setChecked(CameraMode.LOCK_TO_TOP in state)
            with hp.qt_signals_blocked(self._menu_camera_left):
                self._menu_camera_left.setChecked(CameraMode.LOCK_TO_LEFT in state)
            with hp.qt_signals_blocked(self._menu_camera_right):
                self._menu_camera_right.setChecked(CameraMode.LOCK_TO_RIGHT in state)
            with hp.qt_signals_blocked(self._menu_camera_bottom):
                self._menu_camera_bottom.setChecked(CameraMode.LOCK_TO_BOTTOM in state)

    def _handle_trace_file_on_start(self):
        """Start trace of `trace_file_on_start` config set."""
        from napari._qt._qapp_model.qactions._debug import _start_trace
        from napari.utils import perf

        if perf.perf_config:
            path = perf.perf_config.trace_file_on_start
            if path is not None:
                # Config option "trace_file_on_start" means immediately
                # start tracing to that file. This is very useful if you
                # want to create a trace every time you start napari,
                # without having to start it from the debug menu.
                _start_trace(path)

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

    def _toggle_background(self, which: str):
        """Toggle between dark and light backgrounds."""
        if which == "dark":
            background, labels = "black", "white"
        else:
            background, labels = "white", "black"
        self._qt_viewer.canvas.bgcolor = background
        self._qt_viewer.viewer.axis.label_color = labels
        self._qt_viewer.viewer.axis.tick_color = labels

    # def _toggle_command_palette(self):
    #     """Toggle the visibility of the command palette."""
    #     palette = self._qt_window._command_palette
    #     if palette.isVisible():
    #         palette.hide()
    #     else:
    #         palette.update_context(self._qt_window)
    #         palette.show()

    def _toggle_fullscreen(self, event):
        """Toggle fullscreen mode."""
        if self._qt_window.isFullScreen():
            self._qt_window.showNormal()
        else:
            self._qt_window.showFullScreen()

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

    def set_geometry(self, left, top, width, height):
        """Set the geometry of the widget

        Parameters
        ----------
        left : int
            X coordinate of the upper left border.
        top : int
            Y coordinate of the upper left border.
        width : int
            Width of the rectangle shape of the window.
        height : int
            Height of the rectangle shape of the window.
        """
        self._qt_window.setGeometry(left, top, width, height)

    def geometry(self) -> tuple[int, int, int, int]:
        """Get the geometry of the widget

        Returns
        -------
        left : int
            X coordinate of the upper left border.
        top : int
            Y coordinate of the upper left border.
        width : int
            Width of the rectangle shape of the window.
        height : int
            Height of the rectangle shape of the window.
        """
        rect = self._qt_window.geometry()
        return rect.left(), rect.top(), rect.width(), rect.height()

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

        # Resize axis labels now that window is shown
        self._qt_viewer.dims._resize_axis_labels()

        # We want to bring the viewer to the front when
        # A) it is our own event loop OR we are running in jupyter
        # B) it is not the first time a QMainWindow is being created
        app_name = QApplication.instance().applicationName()
        if (app_name == "napari-plot" or in_jupyter()) and self._qt_window.isActiveWindow():
            self.activate()

    def activate(self):
        """Make the viewer the currently active window."""
        self._qt_window.raise_()  # for macOS
        self._qt_window.activateWindow()  # for Windows

    def _update_theme(self, event=None):
        """Update widget color theme."""
        with contextlib.suppress(AttributeError, RuntimeError):
            if event:
                value = event.value
                self._qt_viewer.viewer.theme = value
            else:
                value = self._qt_viewer.viewer.theme

            self._qt_window.setStyleSheet(get_stylesheet(value))

    def _status_changed(self, event):
        """Update status bar."""
        if isinstance(event.value, str):
            self._status_bar.setStatusText(event.value)
        else:
            status_info = event.value
            self._status_bar.setStatusText(
                layer_base=status_info["layer_base"],
                source_type=status_info["source_type"],
                plugin=status_info["plugin"],
                coordinates=status_info["coordinates"],
            )

    def _title_changed(self, event):
        """Update window title."""
        self._qt_window.setWindowTitle(event.value)

    def _help_changed(self, event):
        """Update help message on status bar.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        self._status_bar.setHelpText(event.value)

    def _restart(self):
        """Restart the napari application."""
        self._qt_window.restart()

    def _screenshot(
        self,
        size: ty.Optional[tuple[int, int]] = None,
        scale: ty.Optional[float] = None,
        flash: bool = True,
        canvas_only: bool = False,
        fit_to_data_extent: bool = False,
    ) -> QImage:
        """Capture screenshot of the currently displayed viewer.

        Parameters
        ----------
        flash : bool
            Flag to indicate whether flash animation should be shown after
            the screenshot was captured.
        size : tuple (int, int)
            Size (resolution) of the screenshot. By default, the currently displayed size.
            Only used if `canvas_only` is True.
        scale : float
            Scale factor used to increase resolution of canvas for the screenshot. By default, the currently displayed
             resolution. Only used if `canvas_only` is True.
        canvas_only : bool
            If True, screenshot shows only the image display canvas, and if False include the napari viewer frame in
             the screenshot, By default, True.
        fit_to_data_extent: bool
            Tightly fit the canvas around the data to prevent margins from showing in the screenshot. If False, a
            screenshot of the currently visible canvas will be generated.

        Returns
        -------
        img : QImage
        """
        from napari._qt.utils import add_flash_animation

        canvas = self._qt_viewer.canvas
        prev_size = canvas.size
        camera = self._qt_viewer.viewer.camera
        old_rect = camera.rect
        old_extent = camera.extent
        old_zoom = camera.zoom
        ndisplay = self._qt_viewer.viewer.dims.ndisplay

        # Part 1: validate incompatible parameters
        if not canvas_only and (fit_to_data_extent or size is not None or scale is not None):
            raise ValueError("scale, size, and fit_to_data_extent can only be set for canvas_only screenshots.")
        if fit_to_data_extent and ndisplay > 2:
            raise NotImplementedError("fit_to_data_extent is not yet implemented for 3D view.")
        if size is not None and len(size) != 2:
            raise ValueError(f"screenshot size must be 2 values, got {len(size)}")

        # Part 2: compute canvas size and view based on parameters
        if fit_to_data_extent:
            extent_world = self._qt_viewer.viewer.layers.extent.world[1][-ndisplay:]
            extent_step = min(self._qt_viewer.viewer.layers.extent.step[-ndisplay:])
            size = extent_world / extent_step + 1
        size = np.asarray(size) / self._qt_window.devicePixelRatio() if size is not None else np.asarray(prev_size)
        if scale is not None:
            # multiply canvas dimensions by the scale factor to get new size
            size *= scale

        # Part 3: take the screenshot
        if canvas_only:
            canvas.size = tuple(size.astype(int))
            if fit_to_data_extent:
                # tight view around data
                self._qt_viewer.viewer.reset_view(margin=0)
            try:
                img = canvas.screenshot()
                if flash:
                    add_flash_animation(self._qt_viewer._welcome_widget)
            finally:
                # make sure we always go back to the right canvas size
                canvas.size = prev_size
                camera.rect = old_rect
                camera.extent = old_extent
                camera.zoom = old_zoom
        else:
            img = self._qt_window.grab().toImage()
            if flash:
                add_flash_animation(self._qt_window)
        return img

    def export_figure(
        self,
        path: ty.Optional[str] = None,
        scale: float = 1,
        flash=True,
    ) -> np.ndarray:
        """Export an image of the full extent of the displayed layer data.

        This function finds a tight boundary around the data, resets the view
        around that boundary (and, when scale=1, such that 1 captured pixel is
        equivalent to one data pixel), takes a screenshot, then restores the
        previous zoom and canvas sizes. Currently, only works when 2 dimensions
        are displayed.

        Parameters
        ----------
        path : str, optional
            Filename for saving screenshot image.
        scale : float
            Scale factor used to increase resolution of canvas for the
            screenshot. By default, a scale of 1.
        flash : bool
            Flag to indicate whether flash animation should be shown after
            the screenshot was captured.
            By default, True.

        Returns
        -------
        image : array
            Numpy array of type ubyte and shape (h, w, 4). Index [0, 0] is the
            upper-left corner of the rendered region.
        """
        from napari.utils.io import imsave

        if not isinstance(scale, (float, int)):
            raise TypeError("Scale must be a float or an int.")
        img = QImg2array(
            self._screenshot(
                scale=scale,
                flash=flash,
                canvas_only=True,
                fit_to_data_extent=True,
            )
        )
        if path is not None:
            imsave(path, img)
        return img

    def export_rois(
        self,
        rois: list[np.ndarray],
        paths: ty.Optional[ty.Union[str, Path, list[ty.Union[str, Path]]]] = None,
        scale: ty.Optional[float] = None,
    ):
        """Export the given rectangular rois to specified file paths.

        For each shape, moves the camera to the center of the shape
        and adjust the canvas size to fit the shape.
        Note: The shape height and width can be of type float.
        However, the canvas size only accepts a tuple of integers.
        This can result in slight misalignment.

        Parameters
        ----------
        rois: list[np.ndarray]
            A list of arrays  with each being of shape (4, 2) representing
            a rectangular roi.
        paths: str, Path, list[str, Path], optional
            Where to save the rois. If a string or a Path, a directory will
            be created if it does not exist yet and screenshots will be
            saved with filename `roi_{n}.png` where n is the nth roi. If
            paths is a list of either string or paths, these need to be the
            full paths of where to store each individual roi. In this case
            the length of the list and the number of rois must match.
            If None, the screenshots will only be returned and not saved
            to disk.
        scale: float, optional
            Scale factor used to increase resolution of canvas for the screenshot.
            By default, uses the displayed scale.

        Returns
        -------
        screenshot_list: list
            The list with roi screenshots.

        """
        from napari.utils.geometry import get_center_bbox

        if paths is not None and isinstance(paths, list) and len(paths) != len(rois):
            raise ValueError("The number of file paths does not match the number of ROI shapes")

        if isinstance(paths, (str, Path)):
            storage_dir = Path(paths).expanduser()
            storage_dir.mkdir(parents=True, exist_ok=True)
            paths = [storage_dir / f"roi_{n}.png" for n in range(len(rois))]

        if self._qt_viewer.viewer.dims.ndisplay > 2:
            raise NotImplementedError("'export_rois' is not implemented for 3D view.")

        screenshot_list = []
        camera = self._qt_viewer.viewer.camera
        start_camera_center = camera.center
        start_camera_zoom = camera.zoom
        canvas = self._qt_viewer.canvas
        prev_size = canvas.size

        visible_dims = list(self._qt_viewer.viewer.dims.displayed)
        step = min(self._qt_viewer.viewer.layers.extent.step[visible_dims])

        for index, roi in enumerate(rois):
            center_coord, height, width = get_center_bbox(roi)
            camera.center = center_coord
            canvas.size = (int(height / step), int(width / step))

            camera.zoom = 1 / step
            path = paths[index] if paths is not None else None
            screenshot_list.append(self.screenshot(path=path, canvas_only=True, scale=scale))

        canvas.size = prev_size
        camera.center = start_camera_center
        camera.zoom = start_camera_zoom

        return screenshot_list

    def screenshot(self, path=None, size=None, scale=None, flash=True, canvas_only=False):
        """Take currently displayed viewer and convert to an image array.

        Parameters
        ----------
        path : str
            Filename for saving screenshot image.
        size : tuple (int, int)
            Size (resolution) of the screenshot. By default, the currently displayed size.
            Only used if `canvas_only` is True.
        scale : float
            Scale factor used to increase resolution of canvas for the screenshot. By default, the currently displayed resolution.
            Only used if `canvas_only` is True.
        flash : bool
            Flag to indicate whether flash animation should be shown after
            the screenshot was captured.
        canvas_only : bool
            If True, screenshot shows only the image display canvas, and
            if False include the napari viewer frame in the screenshot,
            By default, True.

        Returns
        -------
        image : array
            Numpy array of type ubyte and shape (h, w, 4). Index [0, 0] is the
            upper-left corner of the rendered region.
        """
        from napari.utils.io import imsave

        img = QImg2array(self._screenshot(size, scale, flash, canvas_only))
        if path is not None:
            imsave(path, img)  # scikit-image imsave method
        return img

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

    def _teardown(self):
        """Carry out various teardown tasks such as event disconnection."""

    def close(self):
        """Close the viewer window and cleanup sub-widgets."""
        # Someone is closing us twice? Only try to delete self._qt_window
        # if we still have one.
        if hasattr(self, "_qt_window"):
            self._teardown()
            self._qt_viewer.close()
            self._qt_window.close()
            del self._qt_window

    def _screenshot_dialog(self):
        """Save screenshot of current display with viewer, default .png"""
        dial = ScreenshotDialog(self.screenshot, self._qt_viewer)

        if dial.exec_():
            pass
