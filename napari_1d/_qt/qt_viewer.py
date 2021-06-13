"""Qt widget that embeds the canvas"""
# Third-party imports
from typing import Tuple

import numpy as np

from napari._qt.containers import QtLayerList
from napari._qt.utils import (
    QImg2array,
    add_flash_animation,
    circle_pixmap,
    square_pixmap,
)
from napari.utils.interactions import (
    ReadOnlyWrapper,
    mouse_move_callbacks,
    mouse_press_callbacks,
    mouse_release_callbacks,
    mouse_wheel_callbacks,
)
from napari.utils.key_bindings import KeymapHandler
from qtpy.QtCore import QCoreApplication, Qt
from qtpy.QtGui import QCursor, QGuiApplication
from qtpy.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout

from .qt_layer_controls_container import QtLayerControlsContainer
from .qt_layer_buttons import QtLayerButtons, QtViewerButtons
from .qt_toolbar import QtViewToolbar
from .._vispy.utils import create_vispy_visual
from .._vispy.vispy_axis_label_visual import VispyXAxisVisual, VispyYAxisVisual
from .._vispy.vispy_camera import VispyCamera
from .._vispy.vispy_canvas import VispyCanvas
from .._vispy.vispy_grid_lines_visual import VispyGridLinesVisual
from .._vispy.vispy_span_visual import VispySpanVisual
from .._vispy.vispy_text_visual import VispyTextVisual


class QtViewer(QWidget):
    """Qt view for the napari Viewer model.

    Parameters
    ----------
    viewer : imimspy.napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.

    Attributes
    ----------
    canvas : vispy.scene.SceneCanvas
        Canvas for rendering the current view.
    layer_to_visual : dict
        Dictionary mapping napari layers with their corresponding vispy_layers.
    view : vispy scene widget
        View displayed by vispy canvas. Adds a vispy ViewBox as a child widget.
    viewer : imimsui.napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.
    """

    def __init__(self, viewer, parent=None, disable_controls: bool = False, **kwargs):
        super().__init__(parent=parent)  # noqa
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAcceptDrops(False)
        QCoreApplication.setAttribute(
            Qt.AA_UseStyleSheetPropagationInWidgetStyles, True
        )

        # handle to the viewer instance
        self.viewer = viewer

        # keyboard handler
        self._key_map_handler = KeymapHandler()
        self._key_map_handler.keymap_providers = [self.viewer]
        self._key_bindings_dialog = None
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

        # setup view
        self._set_view()

        # setup camera
        self._set_camera()

        # add layers
        for layer in self.viewer.layers:
            self._add_layer(layer)

        # Add axes, scalebar, grid and colorbar visuals
        self._add_visuals()

        # add extra initialisation
        self._post_init()

    def __getattr__(self, name):
        return object.__getattribute__(self, name)

    @property
    def pos_offset(self) -> Tuple[int, int]:
        """Window offset"""
        return 0, 0

    def _create_canvas(self) -> None:
        """Create the canvas and hook up events."""
        self.canvas = VispyCanvas(
            keys=None,
            vsync=True,
            parent=self,
            size=self.viewer._canvas_size[::-1],
        )
        self.canvas.events.reset_view.connect(self.viewer.reset_view)
        self.canvas.connect(self.on_mouse_move)
        self.canvas.connect(self.on_mouse_press)
        self.canvas.connect(self.on_mouse_release)
        self.canvas.connect(self._key_map_handler.on_key_press)
        self.canvas.connect(self._key_map_handler.on_key_release)
        self.canvas.connect(self.on_mouse_wheel)
        self.canvas.connect(self.on_draw)
        self.canvas.connect(self.on_resize)

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

    def _set_layout(self, add_toolbars: bool = True, **kwargs):
        # set in main canvas
        # main_widget = QWidget()  # noqa
        image_layout = QVBoxLayout()
        image_layout.addWidget(self.canvas.native, stretch=True)

        # view widget
        main_layout = QHBoxLayout()
        main_layout.addLayout(image_layout)

        if add_toolbars:
            main_layout.addWidget(self.viewerToolbar.toolbar_right)
        else:
            self.viewerToolbar.setVisible(False)
            self.viewerToolbar.toolbar_left.setVisible(False)
            self.viewerToolbar.toolbar_right.setVisible(False)
            main_layout.setSpacing(0)
            main_layout.setMargin(0)

        self.setLayout(main_layout)

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
        self.camera = VispyCamera(
            self.view, self.viewer.camera, self.viewer.dims, self.viewer
        )
        self.canvas.connect(self.camera.on_draw)

        self.camera.camera.events.box_press.connect(self._on_boxzoom)
        self.camera.camera.events.box_move.connect(self._on_boxzoom_move)

    def _on_boxzoom(self, event):
        """Update boxzoom visibility."""
        self.viewer.span.visible = event.visible
        if not event.visible:
            self.viewer.span.position = 0, 0

    def _on_boxzoom_move(self, event):
        """Update boxzoom"""
        rect = event.rect
        self.viewer.span.position = rect[0], rect[1]

    def _add_visuals(self) -> None:
        """Add visuals for axes, scale bar"""
        # add span
        self.span = VispySpanVisual(self.viewer, parent=self.view, order=1e5)

        # add gridlines
        self.grid_lines = VispyGridLinesVisual(self.viewer, parent=self.view, order=1e6)

        # add x-axis widget
        self.x_axis = VispyXAxisVisual(self.viewer, parent=self.view, order=1e6 + 1)
        self.grid.add_widget(self.x_axis.node, row=1, col=1)
        self.x_axis.node.link_view(self.view)
        self.x_axis.node.height_max = self.viewer.axis.x_max_size
        self.x_axis.interactive = True

        # add y-axis widget
        self.y_axis = VispyYAxisVisual(self.viewer, parent=self.view, order=1e6 + 1)
        self.grid.add_widget(self.y_axis.node, row=0, col=0)
        self.y_axis.node.link_view(self.view)
        self.y_axis.node.width_max = self.viewer.axis.y_max_size
        self.y_axis.interactive = True

        # add label
        self.text_overlay = VispyTextVisual(
            self, self.viewer, parent=self.view, order=1e6 + 2
        )

        with self.canvas.modify_context() as canvas:
            canvas.x_axis = self.x_axis
            canvas.y_axis = self.y_axis

    def _set_view(self):
        """Set view"""
        self.grid = self.canvas.central_widget.add_grid(spacing=0)
        self.view = self.grid.add_view(row=0, col=1)
        with self.canvas.modify_context() as canvas:
            canvas.grid = self.grid
            canvas.view = self.view

    def _post_init(self):
        """Complete initialization with post-init events"""
        # self.viewerToolbar.connect_toolbar()

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

        # If a QtAboutKeyBindings exists, update its text.
        if self._key_bindings_dialog is not None:
            self._key_bindings_dialog.update_active_layer()

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
        from skimage.io import imsave

        img = QImg2array(self.canvas.native.grabFramebuffer())
        if path is not None:
            imsave(path, img)  # scikit-image imsave method
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
        from .layer_controls.qt_layers_dialog import DialogLineControls

        if self._disable_controls:
            return

        if self._layers_controls_dialog is None:
            self._layers_controls_dialog = DialogLineControls(self)
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
            self._layers_controls_dialog.setVisible(
                not self._layers_controls_dialog.isVisible()
            )

    def on_open_key_bindings_dialog(self, _event=None):
        """Show key bindings dialog"""
        from napari._qt.dialogs.qt_about_key_bindings import QtAboutKeyBindings

        if self._key_bindings_dialog is None:
            self._key_bindings_dialog = QtAboutKeyBindings(
                self.viewer, self._key_map_handler, parent=self
            )
        # make sure the dialog is shown
        self._key_bindings_dialog.show()
        # make sure the the dialog gets focus
        self._key_bindings_dialog.raise_()  # for macOS
        self._key_bindings_dialog.activateWindow()  # for Windows

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

    def on_resize(self, event):
        """Called whenever canvas is resized.

        event : vispy.util.event.Event
            The vispy event that triggered this method.
        """
        self.viewer._canvas_size = tuple(self.canvas.size[::-1])

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
        nd = self.viewer.dims.ndisplay
        transform = self.view.camera.transform.inverse
        mapped_position = transform.map(position)[:nd]
        position_world_slice = mapped_position[::-1]

        position_world = list(self.viewer.dims.point)
        for i, d in enumerate(self.viewer.dims.displayed):
            position_world[d] = position_world_slice[i]
        return tuple(position_world)

    def on_draw(self, _event):
        """Called whenever the canvas is drawn.

        This is triggered from vispy whenever new data is sent to the canvas or
        the camera is moved and is connected in the `QtViewer`.
        """
        for layer in self.viewer.layers:
            if layer.ndim <= self.viewer.dims.ndim:
                layer._update_draw(
                    scale_factor=1 / self.viewer.camera.zoom,
                    corner_pixels=self._canvas_corners_in_world[:, -layer.ndim :],
                    shape_threshold=self.canvas.size,
                )

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
        raise NotImplementedError("Must implement method")
