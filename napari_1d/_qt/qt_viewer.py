"""Qt widget that embeds the canvas"""
from contextlib import suppress
from typing import Tuple

import numpy as np
from napari._qt.containers import QtLayerList
from napari._qt.dialogs.screenshot_dialog import ScreenshotDialog
from napari._qt.utils import QImg2array, add_flash_animation, circle_pixmap, square_pixmap
from napari._qt.widgets.qt_viewer_dock_widget import QtViewerDockWidget
from napari.utils.interactions import (
    ReadOnlyWrapper,
    mouse_move_callbacks,
    mouse_press_callbacks,
    mouse_release_callbacks,
    mouse_wheel_callbacks,
)
from napari.utils.key_bindings import KeymapHandler
from napari.utils.theme import get_theme
from qtpy.QtCore import QCoreApplication, Qt
from qtpy.QtGui import QCursor, QGuiApplication
from qtpy.QtWidgets import QHBoxLayout, QSplitter, QVBoxLayout, QWidget

from .._vispy.camera import VispyCamera
from .._vispy.canvas import VispyCanvas
from .._vispy.overlays.axis import VispyXAxisVisual, VispyYAxisVisual
from .._vispy.overlays.grid_lines import VispyGridLinesVisual
from .._vispy.overlays.text import VispyTextVisual
from .._vispy.tools.drag import VispyDragTool
from .._vispy.utils.visual import create_vispy_visual
from .layer_controls.qt_layer_controls_container import QtLayerControlsContainer
from .qt_layer_buttons import QtLayerButtons, QtViewerButtons
from .qt_toolbar import QtViewToolbar


class QtViewer(QSplitter):
    """Qt view for the napari Viewer model.

    Parameters
    ----------
    viewer : napari_1d.components.ViewerModel
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

    _pos_offset = (0, 0)
    _pos_offset_set = False

    def __init__(self, viewer, parent=None, disable_controls: bool = False, **kwargs):
        super().__init__(parent=parent)  # noqa
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAcceptDrops(False)
        QCoreApplication.setAttribute(Qt.AA_UseStyleSheetPropagationInWidgetStyles, True)

        # handle to the viewer instance
        self.viewer = viewer

        # keyboard handler
        self._key_map_handler = KeymapHandler()
        self._key_map_handler.keymap_providers = [self.viewer]
        self._disable_controls = disable_controls
        self._layers_controls_dialog = None

        # This dictionary holds the corresponding vispy visual for each layer
        self.layer_to_visual = {}

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

    @property
    def pos_offset(self) -> Tuple[int, int]:
        """Pixel offset"""
        # because we've added y-axis to the canvas, the central view is slightly offset from the (0, 0) position,
        # in which case when we try to do any fancy drawing, it draws points slightly away from the place its meant
        # to. Subtracting the y-axis width is sufficient to correct for the error.
        return self._pos_offset

    def on_resize(self, event):
        """Update cached x-axis offset"""
        # the first time its being set, it happens too quickly for the canvas to be fully rendered, so instead its set
        # from the model attribute rather than the rect width
        if not self._pos_offset_set:
            self._pos_offset = int(self.viewer.axis.y_max_size), 20
            self._pos_offset_set = False
        else:
            self._pos_offset = int(self.y_axis.node.rect.width), 20
        self.viewer._canvas_size = tuple(self.canvas.size[::-1])

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

        self.canvas.connect(self.on_mouse_move)
        self.canvas.connect(self.on_mouse_press)
        self.canvas.connect(self.on_mouse_release)
        self.canvas.connect(self._key_map_handler.on_key_press)
        self.canvas.connect(self._key_map_handler.on_key_release)
        self.canvas.connect(self.on_mouse_wheel)
        self.canvas.connect(self.on_draw)
        self.canvas.connect(self.on_resize)
        self.canvas.bgcolor = get_theme(self.viewer.theme, False).canvas.as_rgb_tuple()
        theme = self.viewer.events.theme

        on_theme_change = self.canvas._on_theme_change
        theme.connect(on_theme_change)

        def _disconnect():
            # strange EventEmitter has no attribute _callbacks errors sometimes
            # maybe some sort of cleanup race condition?
            with suppress(AttributeError):
                theme.disconnect(on_theme_change)

        self.canvas.destroyed.connect(_disconnect)

    def _create_widgets(self, **kwargs):
        """Create ui widgets"""
        # widget showing layer controls
        self.controls = QtLayerControlsContainer(self.viewer)
        # widget showing current layers
        self.layers = QtLayerList(self.viewer.layers)
        # widget showing layer buttons (e.g. add new shape)
        self.layerButtons = QtLayerButtons(self.viewer)
        # viewer buttons
        self.viewerButtons = QtViewerButtons(self.viewer, self)
        # toolbar
        self.viewerToolbar = QtViewToolbar(self.viewer, self, **kwargs)

    def _set_layout(self, add_toolbars: bool = True, dock_controls: bool = False, **kwargs):
        # set in main canvas
        canvas_layout = QHBoxLayout()
        canvas_layout.addWidget(self.canvas.native, stretch=True)

        if add_toolbars:
            canvas_layout.addWidget(self.viewerToolbar.toolbar_right)
        else:
            self.viewerToolbar.setVisible(False)
            self.viewerToolbar.toolbar_right.setVisible(False)
            canvas_layout.setSpacing(0)
            canvas_layout.setMargin(0)

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
            )
            self.dockLayerList.setVisible(True)
            self.dockLayerControls = QtViewerDockWidget(
                self,
                self.controls,
                name="Layer controls",
                area="left",
                allowed_areas=["left", "right"],
                object_name="layer controls",
            )
            self.dockLayerControls.setVisible(True)

            self.dockLayerControls.visibilityChanged.connect(self._constrain_width)
            self.dockLayerList.setMaximumWidth(258)
            self.dockLayerList.setMinimumWidth(258)

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 2)
        main_layout.addLayout(canvas_layout)
        main_layout.setSpacing(3)
        main_widget.setLayout(main_layout)

        self.setOrientation(Qt.Vertical)
        self.addWidget(main_widget)

    def _set_events(self):
        # bind events
        self.viewer.layers.selection.events.active.connect(self._on_active_change)
        self.viewer.camera.events.interactive.connect(self._on_interactive)
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
        self.grid_lines = VispyGridLinesVisual(self.viewer, parent=self.view, order=1e6)

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

        # add label
        self.text_overlay = VispyTextVisual(self, self.viewer, parent=self.view, order=1e6 + 2)

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

    def _constrain_width(self, _event):
        """Allow the layer controls to be wider, only if floated.

        Parameters
        ----------
        _event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        if self.dockLayerControls.isFloating():
            self.controls.setMaximumWidth(700)
        else:
            self.controls.setMaximumWidth(220)

    def _on_active_change(self, _event=None):
        """When active layer changes change keymap handler.

        Parameters
        ----------
        _event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        active_layer = self.viewer.layers.selection.active
        if active_layer in self._key_map_handler.keymap_providers:
            self._key_map_handler.keymap_providers.remove(active_layer)

        if active_layer is not None:
            self._key_map_handler.keymap_providers.insert(0, active_layer)

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
        vispy_layer = create_vispy_visual(layer)
        vispy_layer.node.parent = self.view.scene
        vispy_layer.order = len(self.viewer.layers) - 1
        self.layer_to_visual[layer] = vispy_layer

    def _remove_layer(self, event):
        """When a layer is removed, remove its parent.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        layer = event.value
        vispy_layer = self.layer_to_visual[layer]
        vispy_layer.close()
        del vispy_layer
        self._reorder_layers(None)

    def _reorder_layers(self, _event):
        """When the list is reordered, propagate changes to draw order.

        Parameters
        ----------
        _event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        for i, layer in enumerate(self.viewer.layers):
            vispy_layer = self.layer_to_visual[layer]
            vispy_layer.order = i
        self.canvas._draw_order.clear()
        self.canvas.update()

    def on_save_figure(self, path=None):
        """Export figure"""
        from napari._qt.dialogs.screenshot_dialog import ScreenshotDialog

        dialog = ScreenshotDialog(self.screenshot, self, history=[])
        if dialog.exec_():
            pass

    def screenshot(self, path=None):
        """Take currently displayed screen and convert to an image array.

        Parameters
        ----------
        path : str
            Filename for saving screenshot image.

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
            if size < 8 or size > (min(*self.viewer.window.qt_viewer.canvas.size) - 4):
                q_cursor = self._cursors["cross"]
            else:
                q_cursor = QCursor(square_pixmap(size))
        elif cursor == "circle":
            q_cursor = QCursor(circle_pixmap(size))
        else:
            q_cursor = self._cursors[cursor]

        self.canvas.native.setCursor(q_cursor)

    def on_open_controls_dialog(self, event=None):
        """Open dialog responsible for layer settings"""
        from .layer_controls.qt_layers_dialog import Napari1dControls

        if self._disable_controls:
            return

        if self._layers_controls_dialog is None:
            self._layers_controls_dialog = Napari1dControls(self)
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

        # Update the cursor position
        self.viewer.cursor.position = self._map_canvas2world(event.pos)

        # Add the cursor position to the event
        event.position = self.viewer.cursor.position

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
        position[0] -= self.pos_offset[0]
        position[1] -= self.pos_offset[1]
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
        dial = ScreenshotDialog(self.screenshot, self)

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

    def closeEvent(self, event):
        """Cleanup and close.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self.layers.close()
        self.canvas.native.deleteLater()
        event.accept()
