"""Qt widget that embeds the canvas"""
from __future__ import annotations

import logging
import sys
import typing as ty
import warnings
import weakref
from pathlib import Path
from types import FrameType
from weakref import WeakSet, ref

import napari.layers as n_layers
from napari._qt.containers import QtLayerList
from napari._qt.dialogs.screenshot_dialog import ScreenshotDialog
from napari._qt.utils import QImg2array, add_flash_animation
from napari._qt.widgets.qt_dims import QtDims
from napari._qt.widgets.qt_viewer_dock_widget import QtViewerDockWidget
from napari.utils.key_bindings import KeymapHandler
from napari.utils.notifications import show_info
from PyQt6.QtCore import QUrl
from qtpy.QtCore import QCoreApplication, Qt
from qtpy.QtGui import QGuiApplication
from qtpy.QtWidgets import QHBoxLayout, QSplitter, QVBoxLayout, QWidget
from superqt import ensure_main_thread

from napari_plot._qt.layer_controls.qt_layer_controls_container import (
    QtLayerControlsContainer,
)
from napari_plot._qt.qt_layer_buttons import QtLayerButtons, QtViewerButtons
from napari_plot._qt.qt_toolbar import QtViewToolbar
from napari_plot._qt.qt_welcome import QtWidgetOverlay
from napari_plot._vispy.canvas import VispyCanvas
from napari_plot._vispy.utils.visual import create_vispy_layer

if ty.TYPE_CHECKING:
    from napari_plot.components.viewer_model import ViewerModel


class QtViewer(QSplitter):
    """Qt view for the napari Viewer model.

    Parameters
    ----------
    viewer : napari_plot.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.

    Attributes
    ----------
    canvas : vispy.scene.SceneCanvas
        Canvas for rendering the current view.
    view : vispy scene widget
        View displayed by vispy canvas. Adds a vispy ViewBox as a child widget.
    viewer : napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.
    """

    _instances = WeakSet()
    _console = None

    def __init__(
        self,
        viewer: ViewerModel,
        parent=None,
        disable_controls: bool = False,
        show_welcome_screen: bool = False,
        **kwargs,
    ):
        super().__init__(parent=parent)
        self._instances.add(self)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAcceptDrops(False)
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseStyleSheetPropagationInWidgetStyles, True)

        self._show_welcome_screen = show_welcome_screen

        # handle to the viewer instance
        self.viewer = viewer
        self.dims = QtDims(self.viewer.dims)

        # keyboard handler
        self._key_map_handler = KeymapHandler()
        self._key_map_handler.keymap_providers = [self.viewer]
        self._console_backlog = []
        self._console = None

        self._disable_controls = disable_controls
        self._layers_controls_dialog = None

        # create ui widgets
        self._create_widgets(**kwargs)

        # create main vispy canvas
        self._create_canvas()

        # set ui
        self._set_layout(**kwargs)

        # setup events
        self._set_events()

        # bind shortcuts stored in settings last.
        self._bind_shortcuts()

        for layer in self.viewer.layers:
            self._add_layer(layer)

    def __getattr__(self, name):
        return object.__getattribute__(self, name)

    def _create_canvas(self) -> None:
        """Create the canvas and hook up events."""
        self.canvas = VispyCanvas(
            viewer=self.viewer,
            parent=self,
            key_map_handler=self._key_map_handler,
            size=self.viewer._canvas_size,
            autoswap=True,
        )

    def _create_widgets(self, **kwargs):
        """Create ui widgets"""
        # widget showing layer controls
        self.controls = QtLayerControlsContainer(self.viewer)
        # widget showing current layers
        self.layers = QtLayerList(self.viewer.layers)
        # widget showing layer buttons (e.g. add new shape)
        self.layerButtons = QtLayerButtons(self.viewer)
        # viewer buttons
        self.viewerButtons = QtViewerButtons(self.viewer, self, **kwargs)
        # toolbar
        self.viewerToolbar = QtViewToolbar(self.viewer, self, **kwargs)

    def _set_layout(
        self,
        add_toolbars: bool = True,
        dock_controls: bool = False,
        dock_console=False,
        dock_camera=False,
        dock_axis=False,
        **kwargs,
    ):
        # set in main canvas
        widget = QWidget()
        canvas_layout = QHBoxLayout(widget)
        canvas_layout.addWidget(self.canvas.native, stretch=True)

        # Stacked widget to provide a welcome page
        self._welcome_widget = QtWidgetOverlay(self, widget)
        self._welcome_widget.set_welcome_visible(self._show_welcome_screen)
        self._welcome_widget.sig_dropped.connect(self.dropEvent)
        self._welcome_widget.leave.connect(self._leave_canvas)
        self._welcome_widget.enter.connect(self._enter_canvas)

        if add_toolbars:
            canvas_layout.addWidget(self.viewerToolbar.toolbar_right)
        else:
            self.viewerToolbar.setVisible(False)
            self.viewerToolbar.toolbar_right.setVisible(False)
            canvas_layout.setSpacing(0)
            canvas_layout.setContentsMargins(0, 0, 0, 0)

        if dock_controls:
            layer_list = QWidget()
            layer_list.setObjectName("layerList")
            layer_list_layout = QVBoxLayout()
            layer_list_layout.addWidget(self.layerButtons)
            layer_list_layout.addWidget(self.layers)
            layer_list_layout.addWidget(self.viewerButtons)
            layer_list_layout.setContentsMargins(8, 4, 8, 6)
            layer_list.setLayout(layer_list_layout)

            self.dockLayerList = QtViewerDockWidget(
                self,
                layer_list,
                name="Layer list",
                area="left",
                allowed_areas=["left", "right"],
                object_name="layer list",
                close_btn=False,
            )
            self.dockLayerList.setVisible(True)
            self.dockLayerControls = QtViewerDockWidget(
                self,
                self.controls,
                name="Layer controls",
                area="left",
                allowed_areas=["left", "right"],
                object_name="layer controls",
                close_btn=False,
            )
            self.dockLayerControls.setVisible(True)
            # self.dockLayerControls.visibilityChanged.connect(self._constrain_width)
        if dock_console:
            self.dockConsole = QtViewerDockWidget(
                self,
                QWidget(),
                name="Console",
                area="bottom",
                allowed_areas=["top", "bottom"],
                object_name="console",
                close_btn=False,
            )
            self.dockConsole.setVisible(False)
            # because the console is loaded lazily in the @getter, this line just
            # gets (or creates) the console when the dock console is made visible.
            self.dockConsole.visibilityChanged.connect(self._ensure_connect)
        if dock_camera:
            from napari_plot._qt.component_controls.qt_camera_controls import (
                QtCameraWidget,
            )

            self.dockCamera = QtViewerDockWidget(
                self,
                QtCameraWidget(self.viewer, self),
                name="Camera controls",
                area="right",
                object_name="camera",
                close_btn=False,
            )
            self.dockCamera.setVisible(False)
        if dock_axis:
            from napari_plot._qt.component_controls.qt_axis_controls import QtAxisWidget

            self.dockAxis = QtViewerDockWidget(
                self,
                QtAxisWidget(self.viewer, self),
                name="Axis controls",
                area="right",
                object_name="axis",
                close_btn=False,
            )
            self.dockAxis.setVisible(False)

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 2, 0, 2)
        main_layout.addWidget(self._welcome_widget)
        main_layout.setSpacing(1)

        self.setOrientation(Qt.Orientation.Vertical)
        self.addWidget(main_widget)

    def _set_events(self):
        # bind events
        # self.viewer.layers.events.inserted.connect(self._update_camera_depth)
        # self.viewer.layers.events.removed.connect(self._update_camera_depth)
        # self.viewer.dims.events.ndisplay.connect(self._update_camera_depth)
        self.viewer.layers.events.inserted.connect(self._update_welcome_screen)
        self.viewer.layers.events.removed.connect(self._update_welcome_screen)
        self.viewer.layers.selection.events.active.connect(self._on_active_change)
        self.viewer.layers.events.inserted.connect(self._on_add_layer_change)

    @property
    def layer_to_visual(self):
        """Mapping of Napari layer to Vispy layer. Added for backward compatibility"""
        return self.canvas.layer_to_visual

    def _leave_canvas(self):
        """disable status on canvas leave"""
        self.viewer.status = ""
        self.viewer.mouse_over_canvas = False

    def _enter_canvas(self):
        """enable status on canvas enter"""
        self.viewer.status = "Ready"
        self.viewer.mouse_over_canvas = True

    def _ensure_connect(self):
        # lazy load console
        id(self.console)

    def _bind_shortcuts(self):
        """Bind shortcuts stored in SETTINGS to actions."""
        # from napari.settings import get_settings
        # from napari.utils.action_manager import action_manager
        #
        # for action, shortcuts in get_settings().shortcuts.shortcuts.items():
        #     action_manager.unbind_shortcut(action)
        #     for shortcut in shortcuts:
        #         action_manager.bind_shortcut(action, shortcut)

    @property
    def console(self):
        """QtConsole: iPython console terminal integrated into the napari GUI."""
        if self._console is None and self.dockConsole is not None:
            try:
                import napari
                import numpy as np
                from napari.utils.naming import CallerFrame

                breakpoint_handler = sys.breakpointhook
                from napari_console import QtConsole

                sys.breakpointhook = breakpoint_handler
                import napari_plot

                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore")
                    self.console = QtConsole(self.viewer)
                    self.console.push({"napari": napari, "napari_plot": napari_plot})
                    with CallerFrame(_in_napari) as c:
                        if c.frame.f_globals.get("__name__", "") == "__main__":
                            self.console.push({"np": np})
            except ImportError:
                warnings.warn('napari-console not found. It can be installed with "pip install napari_console"')
                self._console = None
        return self._console

    @console.setter
    def console(self, console):
        self._console = console
        if console is not None:
            self.dockConsole.setWidget(console)
            console.setParent(self.dockConsole)

    @ensure_main_thread
    def _on_slice_ready(self, event):
        """Callback connected to `viewer._layer_slicer.events.ready`.

        Provides updates after slicing using the slice response data.
        This only gets triggered on the async slicing path.
        """
        responses: dict[weakref.ReferenceType[n_layers.Layer], ty.Any] = event.value
        logging.debug("QtViewer._on_slice_ready: %s", responses)
        for weak_layer, response in responses.items():
            if layer := weak_layer():
                # Update the layer slice state to temporarily support behavior
                # that depends on it.
                layer._update_slice_response(response)
                # Update the layer's loaded state before everything else,
                # because they may rely on its updated value.
                layer._update_loaded_slice_id(response.request_id)
                # The rest of `Layer.refresh` after `set_view_slice`, where
                # `set_data` notifies the corresponding vispy layer of the new
                # slice.
                layer.events.set_data()
                layer._update_thumbnail()
                layer._set_highlight(force=True)

    def _weakref_if_possible(self, obj):
        """Create a weakref to obj.

        Parameters
        ----------
        obj : object
            Cannot create weakrefs to many Python built-in datatypes such as
            list, dict, str.

            From https://docs.python.org/3/library/weakref.html: "Objects which
            support weak references include class instances, functions written
            in Python (but not in C), instance methods, sets, frozensets, some
            file objects, generators, type objects, sockets, arrays, deques,
            regular expression pattern objects, and code objects."

        Returns
        -------
        weakref or object
            Returns a weakref if possible.
        """
        try:
            newref = ref(obj)
        except TypeError:
            newref = obj
        return newref

    def _unwrap_if_weakref(self, value):
        """Return value or if that is weakref the object referenced by value.

        Parameters
        ----------
        value : object or weakref
            No-op for types other than weakref.

        Returns
        -------
        unwrapped: object or None
            Returns referenced object, or None if weakref is dead.
        """
        unwrapped = value() if isinstance(value, ref) else value
        return unwrapped

    def add_to_console_backlog(self, variables):
        """Save variables for pushing to console when it is instantiated.

        This function will create weakrefs when possible to avoid holding on to
        too much memory unnecessarily.

        Parameters
        ----------
        variables : dict, str or list/tuple of str
            The variables to inject into the console's namespace. If a dict, a
            simple update is done. If a str, the string is assumed to have
            variable names separated by spaces. A list/tuple of str can also
            be used to give the variable names. If just the variable names are
            give (list/tuple/str) then the variable values looked up in the
            callers frame.
        """
        if isinstance(variables, (str, list, tuple)):
            vlist = variables.split() if isinstance(variables, str) else variables
            vdict = {}
            cf = sys._getframe(2)
            for name in vlist:
                try:
                    vdict[name] = eval(name, cf.f_globals, cf.f_locals)
                except NameError:
                    logging.warning(
                        "Could not get variable %s from %s",
                        name,
                        cf.f_code.co_name,
                    )
        elif isinstance(variables, dict):
            vdict = variables
        else:
            raise TypeError("variables must be a dict/str/list/tuple")
        # weakly reference values if possible
        new_dict = {k: self._weakref_if_possible(v) for k, v in vdict.items()}
        self.console_backlog.append(new_dict)

    def _update_welcome_screen(self):
        """Update welcome screen display based on layer count."""
        if self._show_welcome_screen:
            self._welcome_widget.set_welcome_visible(not self.viewer.layers)

    def set_welcome_visible(self, visible):
        """Show welcome screen widget."""
        self._show_welcome_screen = visible
        self._welcome_widget.set_welcome_visible(visible)

    def _on_active_change(self):
        """When active layer changes change keymap handler."""
        self._key_map_handler.keymap_providers = (
            [self.viewer]
            if self.viewer.layers.selection.active is None
            else [self.viewer.layers.selection.active, self.viewer]
        )

    def _on_add_layer_change(self, event):
        """When a layer is added, set its parent and order.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        layer = event.value
        self._add_layer(layer)

    def _add_layer(self, layer):
        """When a layer is added, set its parent and order.

        Parameters
        ----------
        layer : napari.layers.Layer
            Layer to be added.
        """
        vispy_layer = create_vispy_layer(layer)
        self.canvas.add_layer_visual_mapping(layer, vispy_layer)

    def on_save_figure(self, path=None):
        """Export figure"""
        from napari._qt.dialogs.screenshot_dialog import ScreenshotDialog

        dialog = ScreenshotDialog(self.screenshot, self, history=[])
        if dialog.exec_():
            pass

    def screenshot(self, path=None, flash=True):
        """Take currently displayed screen and convert to an image array.

        Parameters
        ----------
        path : str
            Filename for saving screenshot image.
        flash : bool
            Flag to indicate whether flash animation should be shown after the screenshot was captured.

        Returns
        -------
        image : array
            Numpy array of type ubyte and shape (h, w, 4). Index [0, 0] is the
            upper-left corner of the rendered region.
        """
        from napari.utils.io import imsave

        img = self.canvas.screenshot()
        if path is not None:
            imsave(path, img)
        return img

    def on_open_controls_dialog(self, event=None):
        """Open dialog responsible for layer settings"""
        from napari_plot._qt.layer_controls.qt_layers_dialog import NapariPlotControls

        if self._disable_controls:
            return

        if self._layers_controls_dialog is None:
            self._layers_controls_dialog = NapariPlotControls(self)
        # make sure the dialog is shown
        self._layers_controls_dialog.show()
        # make sure the dialog gets focus
        self._layers_controls_dialog.raise_()  # for macOS
        self._layers_controls_dialog.activateWindow()  # for Windows

    def on_toggle_controls_dialog(self, _event=None):
        """Toggle between on/off state of the layer settings"""
        if self._disable_controls:
            return
        if self._layers_controls_dialog is None:
            self.on_open_controls_dialog()
        else:
            self._layers_controls_dialog.setVisible(not self._layers_controls_dialog.isVisible())

    def on_toggle_console_visibility(self, event=None):
        """Toggle console visible and not visible.

        Imports the console the first time it is requested.
        """
        # force instantiation of console if not already instantiated
        console = self.console
        if console:
            viz = not self.dockConsole.isVisible()
            # modulate visibility at the dock widget level as console is dockable
            self.dockConsole.setVisible(viz)
            if self.dockConsole.isFloating():
                self.dockConsole.setFloating(True)

            if viz:
                self.dockConsole.raise_()

    def _screenshot_dialog(self):
        """Save screenshot of current display, default .png"""
        ScreenshotDialog(self.screenshot, self)

    def clipboard(self):
        """Take a screenshot of the currently displayed viewer and copy the image to the clipboard."""
        img = self.canvas.screenshot()

        cb = QGuiApplication.clipboard()
        cb.setImage(img)
        add_flash_animation(self)

    def keyPressEvent(self, event):
        """Called whenever a key is pressed.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self.canvas._scene_canvas._backend._keyEvent(self.canvas._scene_canvas.events.key_press, event)
        event.accept()

    def keyReleaseEvent(self, event):
        """Called whenever a key is released.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self.canvas._scene_canvas._backend._keyEvent(self.canvas._scene_canvas.events.key_release, event)
        event.accept()

    def dragEnterEvent(self, event):
        """Ignore event if not dragging & dropping a file or URL to open.

        Using event.ignore() here allows the event to pass through the
        parent widget to its child widget, otherwise the parent widget
        would catch the event and not pass it on to the child widget.

        Parameters
        ----------
        event : qtpy.QtCore.QDragEvent
            Event from the Qt context.
        """
        if event.mimeData().hasUrls():
            self._set_drag_status()
            event.accept()
        else:
            event.ignore()

    def _set_drag_status(self):
        """Set dedicated status message when dragging files into viewer"""
        self.viewer.status = "Hold <Alt> key to open plugin selection. Hold <Shift> to open files as stack."

    def _image_from_clipboard(self):
        """Insert image from clipboard as a new layer if clipboard contains an image or link."""
        cb = QGuiApplication.clipboard()
        if cb.mimeData().hasImage():
            image = cb.image()
            if image.isNull():
                return
            arr = QImg2array(image)
            self.viewer.add_image(arr)
            return
        if cb.mimeData().hasUrls():
            show_info("No image in clipboard, trying to open link instead.")
            self._open_from_list_of_urls_data(cb.mimeData().urls(), stack=False, choose_plugin=False)
            return
        if cb.mimeData().hasText():
            show_info("No image in clipboard, trying to parse text in clipboard as a link.")
            url_list = []
            for line in cb.mimeData().text().split("\n"):
                url = QUrl(line.strip())
                if url.isEmpty():
                    continue
                if url.scheme() == "":
                    url.setScheme("file")
                if url.isLocalFile() and not Path(url.toLocalFile()).exists():
                    break
                url_list.append(url)
            else:
                self._open_from_list_of_urls_data(url_list, stack=False, choose_plugin=False)
                return
        show_info("No image or link in clipboard.")

    def dropEvent(self, event):
        """Add local files and web URLS with drag and drop.

        For each file, attempt to open with existing associated reader
        (if available). If no reader is associated or opening fails,
        and more than one reader is available, open dialog and ask
        user to choose among available readers. User can choose to persist
        this choice.

        Parameters
        ----------
        event : qtpy.QtCore.QDropEvent
            Event from the Qt context.
        """
        shift_down = QGuiApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier
        alt_down = QGuiApplication.keyboardModifiers() & Qt.KeyboardModifier.AltModifier

        self._qt_open(
            event.mimeData().urls(),
            stack=bool(shift_down),
            choose_plugin=bool(alt_down),
        )

    def _open_from_list_of_urls_data(self, urls_list: list[QUrl], stack: bool, choose_plugin: bool):
        filenames = []
        for url in urls_list:
            if url.isLocalFile():
                # directories get a trailing "/", Path conversion removes it
                filenames.append(str(Path(url.toLocalFile())))
            else:
                filenames.append(url.toString())

        self._qt_open(
            filenames,
            stack=stack,
            choose_plugin=choose_plugin,
        )

    def _qt_open(
        self,
        filenames: list[str],
        stack: ty.Union[bool, list[list[str]]],
        choose_plugin: bool = False,
        plugin: ty.Optional[str] = None,
        layer_type: ty.Optional[str] = None,
        **kwargs,
    ):
        """Open files, potentially popping reader dialog for plugin selection.

        Call ViewerModel.open and catch errors that could
        be fixed by user making a plugin choice.

        Parameters
        ----------
        filenames : List[str]
            paths to open
        choose_plugin : bool
            True if user wants to explicitly choose the plugin else False
        stack : bool or list[list[str]]
            whether to stack files or not. Can also be a list containing
            files to stack.
        plugin : str
            plugin to use for reading
        layer_type : str
            layer type for opened layers
        """
        # if choose_plugin:
        #     handle_gui_reading(
        #         filenames, self, stack, plugin_override=choose_plugin, **kwargs
        #     )
        #     return
        #
        # try:
        #     self.viewer.open(
        #         filenames,
        #         stack=stack,
        #         plugin=plugin,
        #         layer_type=layer_type,
        #         **kwargs,
        #     )
        # except ReaderPluginError as e:
        #     handle_gui_reading(
        #         filenames,
        #         self,
        #         stack,
        #         e.reader_plugin,
        #         e,
        #         layer_type=layer_type,
        #         **kwargs,
        #     )
        # except MultipleReaderError:
        #     handle_gui_reading(filenames, self, stack, **kwargs)

    def closeEvent(self, event):
        """Cleanup and close.

        Parameters
        ----------
        event : qtpy.QtCore.QCloseEvent
            Event from the Qt context.
        """
        self.layers.close()
        # if the viewer.QtDims object is playing an axis, we need to terminate
        # the AnimationThread before close, otherwise it will cause a segFault
        # or Abort trap. (calling stop() when no animation is occurring is also
        # not a problem)
        self.dims.stop()
        self.canvas.delete()
        if self._console is not None:
            self.console.close()
        self.dockConsole.deleteLater()
        event.accept()


def _in_napari(n: int, frame: FrameType):
    """
    Determines whether we are in napari by looking at:
        1) the frames modules names:
        2) the min_depth
    """
    if n < 2:
        return True
    # in-n-out is used in napari for dependency injection.
    for pref in {"napari.", "napari_plot.", "in_n_out."}:
        if frame.f_globals.get("__name__", "").startswith(pref):
            return True
    return False
