"""Qt widget that embeds the canvas"""
import typing as ty
import warnings
from weakref import WeakSet

import numpy as np

from napari._vispy import create_vispy_overlay
from napari.components.overlays import CanvasOverlay, Overlay, SceneOverlay
from napari._qt.containers import QtLayerList
from napari._qt.dialogs.screenshot_dialog import ScreenshotDialog
from napari._qt.utils import QImg2array, add_flash_animation, circle_pixmap, crosshair_pixmap, square_pixmap
from napari._qt.widgets.qt_viewer_dock_widget import QtViewerDockWidget
from napari.utils._proxies import ReadOnlyWrapper
from napari.utils.interactions import (
    mouse_move_callbacks,
    mouse_press_callbacks,
    mouse_release_callbacks,
    mouse_wheel_callbacks,
    mouse_double_click_callbacks,
)
from napari.utils.key_bindings import KeymapHandler
from napari.utils.theme import get_theme
from qtpy.QtCore import QCoreApplication, Qt
from qtpy.QtGui import QCursor, QGuiApplication
from qtpy.QtWidgets import QHBoxLayout, QSplitter, QVBoxLayout, QWidget

from napari_plot._qt.layer_controls.qt_layer_controls_container import QtLayerControlsContainer
from napari_plot._qt.qt_layer_buttons import QtLayerButtons, QtViewerButtons
from napari_plot._qt.qt_toolbar import QtViewToolbar
from napari_plot._vispy.camera import VispyCamera
from napari_plot._vispy.canvas import VispyCanvas
from napari_plot._vispy.overlays.axis import VispyXAxisVisual, VispyYAxisVisual
from napari_plot._vispy.tools.drag import VispyDragTool
from napari_plot._vispy.utils.visual import create_vispy_layer
from napari_plot._qt.qt_welcome import QtWidgetOverlay

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
    layer_to_visual : dict
        Dictionary mapping napari layers with their corresponding vispy_layers.
    view : vispy scene widget
        View displayed by vispy canvas. Adds a vispy ViewBox as a child widget.
    viewer : napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.
    """

    _instances = WeakSet()
    _console = None

    def __init__(
        self,
        viewer: "ViewerModel",
        parent=None,
        disable_controls: bool = False,
        show_welcome_screen: bool = False,
        **kwargs,
    ):
        super().__init__(parent=parent)  # noqa
        self._instances.add(self)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAcceptDrops(False)
        QCoreApplication.setAttribute(Qt.AA_UseStyleSheetPropagationInWidgetStyles, True)

        self._show_welcome_screen = show_welcome_screen

        # handle to the viewer instance
        self.viewer = viewer

        # keyboard handler
        self._key_map_handler = KeymapHandler()
        self._key_map_handler.keymap_providers = [self.viewer]
        self._console_backlog = []
        self._console = None

        self._disable_controls = disable_controls
        self._layers_controls_dialog = None

        # This dictionary holds the corresponding vispy visual for each layer
        self.layer_to_visual = {}
        self.overlay_to_visual = {}

        self._cursors = {
            "cross": Qt.CrossCursor,
            "forbidden": Qt.ForbiddenCursor,
            "pointing": Qt.PointingHandCursor,
            "horizontal_move": Qt.SizeHorCursor,
            "vertical_move": Qt.SizeVerCursor,
            "standard": QCursor(),
        }

        # create ui widgets
        self._create_widgets(**kwargs)

        # create main vispy canvas
        self._create_canvas()

        # set ui
        self._set_layout(**kwargs)

        # activate layer change
        self._on_active_change()

        # setup events
        self._set_events()

        # add layers
        for layer in self.viewer.layers:
            self._add_layer(layer)

        # setup view
        self._set_view()

        # setup camera
        self._set_camera()

        # Add axes, scalebar, grid and colorbar visuals
        self._add_visuals()

        # add extra initialisation
        self._post_init()

    def __getattr__(self, name):
        return object.__getattribute__(self, name)

    def on_resize(self, event):
        """Update cached x-axis offset"""
        self.viewer._canvas_size = tuple(self.canvas.size[::-1])

    def _add_overlay(self, overlay: Overlay) -> None:
        vispy_overlay = create_vispy_overlay(overlay, viewer=self.viewer)

        if isinstance(overlay, CanvasOverlay):
            vispy_overlay.node.parent = self.view
        elif isinstance(overlay, SceneOverlay):
            vispy_overlay.node.parent = self.view.scene

        self.overlay_to_visual[overlay] = vispy_overlay

    def _create_canvas(self) -> None:
        """Create the canvas and hook up events."""
        self.canvas = VispyCanvas(
            keys=None,
            vsync=True,
            parent=self,
            size=self.viewer._canvas_size[::-1],
        )
        self.canvas.events.reset_view.connect(self.viewer.reset_view)
        self.canvas.events.reset_x.connect(self.viewer.reset_x_view)
        self.canvas.events.reset_y.connect(self.viewer.reset_y_view)

        self.canvas.events.mouse_double_click.connect(self.on_mouse_double_click)
        self.canvas.events.mouse_move.connect(self.on_mouse_move)
        self.canvas.events.mouse_press.connect(self.on_mouse_press)
        self.canvas.events.mouse_release.connect(self.on_mouse_release)
        self.canvas.events.key_press.connect(self._key_map_handler.on_key_press)
        self.canvas.events.key_release.connect(self._key_map_handler.on_key_release)
        self.canvas.events.mouse_wheel.connect(self.on_mouse_wheel)
        self.canvas.events.draw.connect(self.on_draw)
        self.canvas.events.resize.connect(self.on_resize)

        self.canvas.bgcolor = get_theme(self.viewer.theme, False).canvas.as_rgb_tuple()
        theme = self.viewer.events.theme

        on_theme_change = self.canvas._on_theme_change
        theme.connect(on_theme_change)

        self.canvas.destroyed.connect(self._disconnect_theme)

    def _disconnect_theme(self):
        self.viewer.events.theme.disconnect(self.canvas._on_theme_change)

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
            from napari_plot._qt.component_controls.qt_camera_controls import QtCameraWidget

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
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 2)
        main_layout.addWidget(self._welcome_widget)
        main_layout.setSpacing(3)
        main_widget.setLayout(main_layout)

        self.setOrientation(Qt.Vertical)
        self.addWidget(main_widget)

    def _set_events(self):
        # bind events
        self.viewer.layers.events.inserted.connect(self._update_welcome_screen)
        self.viewer.layers.events.removed.connect(self._update_welcome_screen)
        self.viewer.layers.selection.events.active.connect(self._on_active_change)
        # self.viewer.camera.events.mouse_pan.connect(self._on_interactive)
        # self.viewer.camera.events.mouse_zoom.connect(self._on_interactive)
        self.viewer.cursor.events.style.connect(self._on_cursor)
        self.viewer.cursor.events.size.connect(self._on_cursor)
        self.viewer.layers.events.reordered.connect(self._reorder_layers)
        self.viewer.layers.events.inserted.connect(self._on_add_layer_change)
        self.viewer.layers.events.removed.connect(self._remove_layer)

    def _set_camera(self):
        """Setup vispy camera,"""
        self.camera = VispyCamera(self.view, self.viewer.camera, self.viewer)
        self.canvas.connect(self.camera.on_draw)

    def _add_visuals(self) -> None:
        """Add visuals for axes, scale bar"""
        # add span
        self.tool = VispyDragTool(self.viewer, view=self.view, order=1e5)

        # add gridlines
        # self.grid_lines = VispyGridLinesOverlay(self.viewer, parent=self.view, order=1e6)

        # add x-axis widget
        self.x_axis = VispyXAxisVisual(self.viewer, parent=self.view, order=1e6 + 1)
        self.grid.add_widget(self.x_axis.node, row=2, col=1)
        self.x_axis.node.link_view(self.view)
        self.x_axis.node.height_max = self.viewer.axis.x_max_size
        self.x_axis.interactive = True

        # add y-axis widget
        self.y_axis = VispyYAxisVisual(self.viewer, parent=self.view, order=1e6 + 1)
        self.grid.add_widget(self.y_axis.node, row=1, col=0)
        self.y_axis.node.link_view(self.view)
        self.y_axis.node.width_max = self.viewer.axis.y_max_size
        self.y_axis.interactive = True

        for overlay in self.viewer._overlays.values():
            self._add_overlay(overlay)

        # # add label
        # self.text_overlay = VispyTextVisual(self, self.viewer, parent=self.view)

        with self.canvas.modify_context() as canvas:
            canvas.x_axis = self.x_axis
            canvas.y_axis = self.y_axis

    def _set_view(self):
        """Set view"""
        self.grid = self.canvas.central_widget.add_grid(spacing=0)
        self.view = self.grid.add_view(row=1, col=1)

        # this gives small padding to the right of the plot
        self.padding_x = self.grid.add_widget(row=0, col=2)
        self.padding_x.width_max = 20
        # this gives small padding to the top of the plot
        self.padding_y = self.grid.add_widget(row=0, col=0, col_span=2)
        self.padding_y.height_max = 20

        with self.canvas.modify_context() as canvas:
            canvas.grid = self.grid
            canvas.view = self.view

    def _post_init(self):
        """Complete initialization with post-init events"""

    def _leave_canvas(self):
        """disable status on canvas leave"""
        self.viewer.status = ""
        self.viewer.mouse_over_canvas = False

    def _enter_canvas(self):
        """enable status on canvas enter"""
        self.viewer.status = "Ready"
        self.viewer.mouse_over_canvas = True

    # def _constrain_width(self, _event):
    #     """Allow the layer controls to be wider, only if floated.
    #
    #     Parameters
    #     ----------
    #     _event : napari.utils.event.Event
    #         The napari event that triggered this method.
    #     """
    #     if self.dockLayerControls.isFloating():
    #         self.controls.setMaximumWidth(700)
    #     else:
    #         self.controls.setMaximumWidth(220)

    def _ensure_connect(self):
        # lazy load console
        id(self.console)

    @property
    def console(self):
        """QtConsole: iPython console terminal integrated into the napari GUI."""
        if self._console is None and self.dockConsole is not None:
            try:
                import napari
                from napari_console import QtConsole

                import napari_plot

                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore")
                    self.console = QtConsole(self.viewer)
                    self.console.push({"napari": napari, "napari_plot": napari_plot})
            except ImportError:
                warnings.warn("napari-console not found. It can be installed with" ' "pip install napari_console"')
                self._console = None
        return self._console

    @console.setter
    def console(self, console):
        self._console = console
        if console is not None:
            self.dockConsole.setWidget(console)
            console.setParent(self.dockConsole)

    def _on_active_change(self):
        """When active layer changes, change keymap handler."""
        self._key_map_handler.keymap_providers = (
            [self.viewer]
            if self.viewer.layers.selection.active is None
            else [self.viewer.layers.selection.active, self.viewer]
        )

    def _on_add_layer_change(self, event):
        """When a layer is added, set its parent and order."""
        layer = event.value
        self._add_layer(layer)

    def _add_layer(self, layer):
        """When a layer is added, set its parent and order."""
        vispy_layer = create_vispy_layer(layer)
        vispy_layer.node.parent = self.view.scene
        vispy_layer.order = len(self.viewer.layers) - 1
        self.layer_to_visual[layer] = vispy_layer

    def _remove_layer(self, event):
        """When a layer is removed, remove its parent."""
        layer = event.value
        vispy_layer = self.layer_to_visual[layer]
        vispy_layer.close()
        del vispy_layer
        del self.layer_to_visual[layer]
        self._reorder_layers()

    def _reorder_layers(self):
        """When the list is reordered, propagate changes to draw order."""
        first_visible_found = False
        for i, layer in enumerate(self.viewer.layers):
            vispy_layer = self.layer_to_visual[layer]
            vispy_layer.order = i

            # the bottommost visible layer needs special treatment for blending
            if layer.visible and not first_visible_found:
                vispy_layer.first_visible = True
                first_visible_found = True
            else:
                vispy_layer.first_visible = False
            vispy_layer._on_blending_change()

        self.canvas._draw_order.clear()
        self.canvas.update()

    def _update_welcome_screen(self):
        """Update welcome screen display based on layer count."""
        if self._show_welcome_screen:
            self._welcome_widget.set_welcome_visible(not self.viewer.layers)

    def set_welcome_visible(self, visible):
        """Show welcome screen widget."""
        self._show_welcome_screen = visible
        self._welcome_widget.set_welcome_visible(visible)

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

        img = QImg2array(self.canvas.native.grabFramebuffer())
        if path is not None:
            imsave(path, img)
        return img

    def _on_interactive(self, _event):
        """Link interactive attributes of view and viewer.

        Parameters
        ----------
        _event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        self.view.interactive = self.viewer.camera.interactive

    def _on_cursor(self, _event):
        """Set the appearance of the mouse cursor.

        Parameters
        ----------
        _event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        cursor = self.viewer.cursor.style
        # Scale size by zoom if needed
        if self.viewer.cursor.scaled:
            size = self.viewer.cursor.size * self.viewer.camera.zoom
        else:
            size = self.viewer.cursor.size

        if cursor == "square":
            # make sure the square fits within the current canvas
            if size < 8 or size > (min(*self.canvas.size) - 4):
                q_cursor = self._cursors["cross"]
            else:
                q_cursor = QCursor(square_pixmap(size))
        elif cursor == "circle":
            q_cursor = QCursor(circle_pixmap(size))
        elif cursor == "crosshair":
            q_cursor = QCursor(crosshair_pixmap())
        else:
            q_cursor = self._cursors[cursor]

        self.canvas.native.setCursor(q_cursor)

    def on_open_controls_dialog(self, event=None):
        """Open dialog responsible for layer settings"""
        from napari_plot._qt.layer_controls.qt_layers_dialog import NapariPlotControls

        if self._disable_controls:
            return

        if self._layers_controls_dialog is None:
            self._layers_controls_dialog = NapariPlotControls(self)
        # make sure the dialog is shown
        self._layers_controls_dialog.show()
        # make sure the the dialog gets focus
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

    @property
    def _canvas_corners_in_world(self):
        """Location of the corners of canvas in world coordinates.

        Returns
        -------
        corners : 2-tuple
            Coordinates of top left and bottom right canvas pixel in the world.
        """
        # Find corners of canvas in world coordinates
        top_left = self._map_canvas2world([0, 0])
        bottom_right = self._map_canvas2world(self.canvas.size)
        return np.array([top_left, bottom_right])

    def _process_mouse_event(self, mouse_callbacks, event):
        """Called whenever mouse pressed in canvas.
        Parameters
        ----------
        mouse_callbacks : function
            Mouse callbacks function.
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        if event.pos is None:
            return

        # Add the view ray to the event
        event.view_direction = None  # always None because we will display 2d data
        event.up_direction = None  # always None because we will display 2d data

        # Update the cursor position
        self.viewer.cursor._view_direction = event.view_direction
        self.viewer.cursor.position = self._map_canvas2world(event.pos)

        # Add the cursor position to the event
        event.position = self.viewer.cursor.position

        # Add the displayed dimensions to the event
        event.dims_displayed = [0, 1]

        # Put a read only wrapper on the event
        event = ReadOnlyWrapper(event)
        mouse_callbacks(self.viewer, event)

        layer = self.viewer.layers.selection.active
        if layer is not None:
            mouse_callbacks(layer, event)

    def _map_canvas2world(self, position):
        """Map position from canvas pixels into world coordinates.

        Parameters
        ----------
        position : 2-tuple
            Position in canvas (x, y).

        Returns
        -------
        coords : tuple
            Position in world coordinates, matches the total dimensionality
            of the viewer.
        """
        position = list(position)
        position[0] -= self.view.pos[0]
        position[1] -= self.view.pos[1]
        transform = self.view.camera.transform.inverse
        mapped_position = transform.map(position)[:2]
        position_world_slice = mapped_position[::-1]

        position_world = [0, 0]
        for i, d in enumerate((0, 1)):
            position_world[d] = position_world_slice[i]
        return tuple(position_world)

    def on_draw(self, _event):
        """Called whenever the canvas is drawn.

        This is triggered from vispy whenever new data is sent to the canvas or
        the camera is moved and is connected in the `QtViewer`.
        """
        for layer in self.viewer.layers:
            if layer.ndim <= 2:
                layer._update_draw(
                    scale_factor=1 / self.viewer.camera.zoom,
                    corner_pixels_displayed=self._canvas_corners_in_world[:, -layer.ndim :],
                    shape_threshold=self.canvas.size,
                )

    def _screenshot_dialog(self):
        """Save screenshot of current display, default .png"""
        ScreenshotDialog(self.screenshot, self)

    def clipboard(self):
        """Take a screenshot of the currently displayed viewer and copy the image to the clipboard."""
        img = self.canvas.native.grabFramebuffer()

        cb = QGuiApplication.clipboard()
        cb.setImage(img)
        add_flash_animation(self)

    def on_mouse_wheel(self, event):
        """Called whenever mouse wheel activated in canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        self._process_mouse_event(mouse_wheel_callbacks, event)

    def on_mouse_double_click(self, event):
        """Called whenever a mouse double-click happen on the canvas

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method. The `event.type` will always be `mouse_double_click`

        Notes
        -----

        Note that this triggers in addition to the usual mouse press and mouse release.
        Therefore a double click from the user will likely triggers the following event in sequence:

             - mouse_press
             - mouse_release
             - mouse_double_click
             - mouse_release
        """
        self._process_mouse_event(mouse_double_click_callbacks, event)

    def on_mouse_press(self, event):
        """Called whenever mouse pressed in canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        self._process_mouse_event(mouse_press_callbacks, event)

    def on_mouse_move(self, event):
        """Called whenever mouse moves over canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        self._process_mouse_event(mouse_move_callbacks, event)

    def on_mouse_release(self, event):
        """Called whenever mouse released in canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        self._process_mouse_event(mouse_release_callbacks, event)

    def keyPressEvent(self, event):
        """Called whenever a key is pressed.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self.canvas._backend._keyEvent(self.canvas.events.key_press, event)
        event.accept()

    def keyReleaseEvent(self, event):
        """Called whenever a key is released.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self.canvas._backend._keyEvent(self.canvas.events.key_release, event)
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
        self.viewer.status = trans._("Hold <Alt> key to open plugin selection. Hold <Shift> to open files as stack.")

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
        filenames = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                # directories get a trailing "/", Path conversion removes it
                filenames.append(str(Path(url.toLocalFile())))
            else:
                filenames.append(url.toString())

        # TODO: add handlers
        # self._qt_open(
        #     filenames,
        #     stack=bool(shift_down),
        #     choose_plugin=bool(alt_down),
        # )

    def closeEvent(self, event):
        """Cleanup and close.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self.layers.close()
        self.canvas.native.deleteLater()
        if self._console is not None:
            self.console.close()
            self.dockConsole.deleteLater()
        event.accept()
