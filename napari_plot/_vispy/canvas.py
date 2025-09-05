"""Line-specific vispy canvas"""

from __future__ import annotations

import typing as ty
from contextlib import contextmanager
from weakref import WeakSet

import numpy as np
from napari._vispy import create_vispy_overlay
from napari._vispy.mouse_event import NapariMouseEvent
from napari._vispy.utils.cursor import QtCursorVisual
from napari._vispy.utils.gl import get_max_texture_sizes
from napari.components.overlays import CanvasOverlay, Overlay, SceneOverlay
from napari.utils._proxies import ReadOnlyWrapper
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.interactions import (
    mouse_double_click_callbacks,
    mouse_move_callbacks,
    mouse_press_callbacks,
    mouse_release_callbacks,
    mouse_wheel_callbacks,
)
from qtpy.QtCore import QSize
from superqt.utils import qthrottled
from vispy.scene import SceneCanvas as SceneCanvas_, Widget
from vispy.util.event import Event

from napari_plot._vispy.camera import VispyCamera
from napari_plot._vispy.overlays.axis import VispyXAxisVisual, VispyYAxisVisual
from napari_plot._vispy.tools.drag import VispyDragTool

if ty.TYPE_CHECKING:
    import numpy.typing as npt
    from napari._vispy.layers.base import VispyBaseLayer
    from napari._vispy.overlays.base import VispyBaseOverlay
    from napari.layers import Layer
    from napari.utils.key_bindings import KeymapHandler
    from qtpy.QtCore import Qt, pyqtBoundSignal
    from qtpy.QtGui import QCursor, QImage
    from vispy.app.backends._qt import CanvasBackendDesktop
    from vispy.app.canvas import DrawEvent, MouseEvent, ResizeEvent

    from napari_plot.viewer import ViewerModel


class NapariSceneCanvas(SceneCanvas_):
    """Vispy SceneCanvas used to allow for ignoring mouse wheel events with modifiers."""

    view, grid, x_axis, y_axis = None, None, None, None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # enable hover events
        self._send_hover_events = True  # temporary workaround

        self.events.ignore_callback_errors = False
        self.native.setMinimumSize(QSize(200, 200))
        self.context.set_depth_func("lequal")

        with self.modify_context():
            self.grid = self.central_widget.add_grid(spacing=0)
            self.view = self.grid.add_view(row=1, col=1)

            # this gives small padding to the right of the plot
            self.padding_x = self.grid.add_widget(row=0, col=2)
            self.padding_x.width_max = 20
            # this gives small padding to the top of the plot
            self.padding_y = self.grid.add_widget(row=0, col=0, col_span=2)
            self.padding_y.height_max = 20

        # connect events
        self.events.add(reset_view=Event, reset_x=Event, reset_y=Event)

    @contextmanager
    def modify_context(self):
        """Modify context"""
        self.unfreeze()
        yield self
        self.freeze()

    def _process_mouse_event(self, event: MouseEvent) -> None:
        """Ignore mouse wheel events which have modifiers."""
        if event.type == "mouse_wheel" and len(event.modifiers) > 0:
            return
        if event.handled:
            return
        if not hasattr(event, "scale"):
            event.scale = 1.0
        super()._process_mouse_event(event)

    def _on_mouse_double_click(self, event: MouseEvent) -> None:
        """Process mouse double click event"""
        vis = self.visual_at(event.pos)
        # if user double-clicked in the canvas, reset the entire view
        if vis and event.button == 1:
            self.events.reset_view()
        else:
            x, y = event.pos
            x_x, x_y = self.x_axis.node.pos
            y_x, y_y = self.y_axis.node.pos
            # if clicked on the x-axis, reset x-range
            if x > y_x and y > x_y:
                self.events.reset_x()
            # if clicked on the y-axis, reset y-range
            elif x < x_x:
                self.events.reset_y()


class VispyCanvas:
    """Line-based vispy canvas"""

    _instances = WeakSet()
    x_axis, y_axis = None, None

    def __init__(
        self,
        viewer: ViewerModel,
        key_map_handler: KeymapHandler,
        *args,
        **kwargs,
    ):
        self.max_texture_sizes = None
        self._last_theme_color = None
        self.viewer = viewer
        self._background_color_override = None
        self._scene_canvas = NapariSceneCanvas(*args, keys=None, vsync=True, **kwargs)
        self.camera = VispyCamera(self.view, self.viewer.camera, self.viewer)

        self.layer_to_visual: dict[Layer, VispyBaseLayer] = {}
        self._overlay_to_visual: dict[Overlay, VispyBaseOverlay] = {}
        self._key_map_handler = key_map_handler
        self._instances.add(self)
        # Call get_max_texture_sizes() here so that we query OpenGL right now while we know a Canvas exists.
        # Later calls to get_max_texture_sizes() will return the same results because it's using an lru_cache.
        self.max_texture_sizes = get_max_texture_sizes()

        # drag tool
        self.tool = VispyDragTool(self.viewer, view=self.view, order=1e6)

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

        with self._scene_canvas.modify_context():
            self._scene_canvas.x_axis = self.x_axis
            self._scene_canvas.y_axis = self.y_axis

        for overlay in self.viewer._overlays.values():
            self._add_overlay_to_visual(overlay)

        # connect events
        # Connecting events from SceneCanvas
        self._scene_canvas.events.key_press.connect(self._key_map_handler.on_key_press)
        self._scene_canvas.events.key_release.connect(self._key_map_handler.on_key_release)

        # self._scene_canvas.events.draw.connect(self.enable_dims_play)
        self._scene_canvas.events.draw.connect(self.camera.on_draw)
        self._scene_canvas.events.reset_view.connect(self.viewer.reset_view)
        self._scene_canvas.events.reset_x.connect(self.viewer.reset_x_view)
        self._scene_canvas.events.reset_y.connect(self.viewer.reset_y_view)

        self._scene_canvas.events.mouse_double_click.connect(self._on_mouse_double_click)
        self._scene_canvas.events.mouse_move.connect(qthrottled(self._on_mouse_move, timeout=5))
        self._scene_canvas.events.mouse_press.connect(self._on_mouse_press)
        self._scene_canvas.events.mouse_release.connect(self._on_mouse_release)
        self._scene_canvas.events.mouse_wheel.connect(self._on_mouse_wheel)

        self._scene_canvas.events.resize.connect(self.on_resize)
        self._scene_canvas.events.draw.connect(self.on_draw)
        self.viewer.cursor.events.style.connect(self._on_cursor)
        self.viewer.cursor.events.size.connect(self._on_cursor)
        self.viewer.events.theme.connect(self._on_theme_change)
        self.viewer.camera.events.mouse_pan.connect(self._on_interactive)
        self.viewer.camera.events.mouse_zoom.connect(self._on_interactive)
        self.viewer.camera.events.zoom.connect(self._on_cursor)
        self.viewer.layers.events.reordered.connect(self._reorder_layers)
        self.viewer.layers.events.removed.connect(self._remove_layer)

        self.destroyed.connect(self._disconnect_theme)

    @property
    def events(self):
        # This is backwards compatible with the old events system
        # https://github.com/napari/napari/issues/7054#issuecomment-2205548968
        return self._scene_canvas.events

    @property
    def destroyed(self) -> pyqtBoundSignal:
        """Get destroyed signal"""
        return self._scene_canvas._backend.destroyed

    @property
    def native(self) -> CanvasBackendDesktop:
        """Returns the native widget of the Vispy SceneCanvas."""
        return self._scene_canvas.native

    @property
    def screen_changed(self) -> ty.Callable:
        """Bound method returning signal indicating whether the window screen has changed."""
        return self._scene_canvas._backend.screen_changed

    @property
    def background_color_override(self) -> ty.Optional[str]:
        """Background color of VispyCanvas.view returned as hex string. When not None, color is shown instead of
        VispyCanvas.bgcolor. The setter expects str (any in vispy.color.get_color_names) or hex starting
        with # or a tuple | np.array ({3,4},) with values between 0 and 1.

        """
        if self.view in self.central_widget._widgets:
            return self.view.bgcolor.hex
        return None

    @background_color_override.setter
    def background_color_override(self, value: ty.Union[str, np.ndarray, None]) -> None:
        if value:
            self.view.bgcolor = value
        else:
            self.view.bgcolor = None

    @property
    def view(self):
        """Canvas view."""
        return self._scene_canvas.view

    @property
    def grid(self):
        """Canvas grid."""
        return self._scene_canvas.grid

    def _on_theme_change(self, event: Event) -> None:
        self._set_theme_change(event.value)

    def _set_theme_change(self, theme: str) -> None:
        from napari.utils.theme import get_theme

        # Note 1. store last requested theme color, in case we need to reuse it
        # when clearing the background_color_override, without needing to
        # keep track of the viewer.
        # Note 2. the reason for using the `as_hex` here is to avoid
        # `UserWarning` which is emitted when RGB values are above 1
        self._last_theme_color = transform_color(get_theme(theme).canvas.as_hex())[0]
        self.bgcolor = self._last_theme_color

    @property
    def background_color_override(self) -> ty.Optional[str]:
        """Get background color"""
        return self._background_color_override

    @background_color_override.setter
    def background_color_override(self, value):
        self._background_color_override = value
        self.bgcolor = value or self._last_theme_color

    def _on_theme_change(self, event):
        self._set_theme_change(event.value)

    def _set_theme_change(self, theme: str) -> None:
        from napari.utils.theme import get_theme

        # Note 1. store last requested theme color, in case we need to reuse it
        # when clearing the background_color_override, without needing to
        # keep track of the viewer.
        # Note 2. the reason for using the `as_hex` here is to avoid
        # `UserWarning` which is emitted when RGB values are above 1
        self._last_theme_color = transform_color(get_theme(theme).canvas.as_hex())[0]
        self.bgcolor = self._last_theme_color

    def _disconnect_theme(self) -> None:
        self.viewer.events.theme.disconnect(self._on_theme_change)

    @property
    def bgcolor(self) -> str:
        """Background color of the vispy scene canvas as a hex string. The setter expects str
        (any in vispy.color.get_color_names) or hex starting with # or a tuple | np.array ({3,4},)
        with values between 0 and 1."""
        return self._scene_canvas.bgcolor.hex

    @bgcolor.setter
    def bgcolor(self, value: ty.Union[str, npt.ArrayLike]) -> None:
        self._scene_canvas.bgcolor = value

    @property
    def central_widget(self) -> Widget:
        """Overrides SceneCanvas.central_widget to make border_width=0"""
        if self._scene_canvas._central_widget is None:
            self._scene_canvas._central_widget = Widget(
                size=self.size,
                parent=self._scene_canvas.scene,
                border_width=0,
            )
        return self._scene_canvas._central_widget

    @property
    def size(self) -> tuple[int, int]:
        """Return canvas size as tuple (height, width) or accepts size as tuple (height, width)
        and sets Vispy SceneCanvas size as (width, height)."""
        return self._scene_canvas.size[::-1]

    @size.setter
    def size(self, size: tuple[int, int]):
        self._scene_canvas.size = size[::-1]

    @property
    def cursor(self) -> QCursor:
        """Cursor associated with native widget"""
        return self.native.cursor()

    @cursor.setter
    def cursor(self, q_cursor: ty.Union[QCursor, Qt.CursorShape]):
        """Setting the cursor of the native widget"""
        self.native.setCursor(q_cursor)

    def _on_cursor(self) -> None:
        """Create a QCursor based on the napari cursor settings and set in Vispy."""

        cursor = self.viewer.cursor.style
        brush_overlay = self.viewer._brush_circle_overlay
        brush_overlay.visible = False

        if cursor in {"square", "circle", "circle_frozen"}:
            # Scale size by zoom if needed
            size = self.viewer.cursor.size
            if self.viewer.cursor.scaled:
                size *= self.viewer.camera.zoom

            size = int(size)

            # make sure the square fits within the current canvas
            if (size < 8 or size > (min(*self.size) - 4)) and cursor != "circle_frozen":
                self.cursor = QtCursorVisual["cross"].value
            elif cursor.startswith("circle"):
                brush_overlay.size = size
                if cursor == "circle_frozen":
                    self.cursor = QtCursorVisual["standard"].value
                    brush_overlay.position_is_frozen = True
                else:
                    self.cursor = QtCursorVisual.blank()
                    brush_overlay.position_is_frozen = False
                brush_overlay.visible = True
            else:
                self.cursor = QtCursorVisual.square(size)
        elif cursor == "crosshair":
            self.cursor = QtCursorVisual.crosshair()
        else:
            self.cursor = QtCursorVisual[cursor].value

    def delete(self) -> None:
        """Schedules the native widget for deletion"""
        self.native.deleteLater()

    def _on_interactive(self) -> None:
        """Link interactive attributes of view and viewer."""
        # Is this should be changed or renamed?
        self.view.interactive = self.viewer.camera.mouse_zoom or self.viewer.camera.mouse_pan

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

        event.scale = 1.0
        napari_event = NapariMouseEvent(
            event=event,
            view_direction=None,
            up_direction=None,
            camera_zoom=self.viewer.camera.zoom,
            position=self._map_canvas2world(event.pos),
            dims_displayed=[0, 1],
            dims_point=list(self.viewer.dims.point),
            viewbox=(0, 0),
        )

        # Add the view ray to the event
        event.view_direction = None  # always None because we will display 2d data
        event.up_direction = None  # always None because we will display 2d data

        # Update the cursor position
        self.viewer.cursor._view_direction = napari_event.view_direction
        self.viewer.cursor.position = napari_event.position

        # Put a read only wrapper on the event
        read_only_event = ReadOnlyWrapper(napari_event, exceptions=("handled", "scale"))
        mouse_callbacks(self.viewer, read_only_event)

        layer = self.viewer.layers.selection.active
        if layer is not None:
            mouse_callbacks(layer, read_only_event)

        event.handled = napari_event.handled

    def _on_mouse_double_click(self, event):
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

    def _on_mouse_move(self, event):
        """Called whenever mouse moves over canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        self._process_mouse_event(mouse_move_callbacks, event)

    def _on_mouse_press(self, event):
        """Called whenever mouse pressed in canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        self._process_mouse_event(mouse_press_callbacks, event)

    def _on_mouse_release(self, event):
        """Called whenever mouse released in canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        self._process_mouse_event(mouse_release_callbacks, event)

    def _on_mouse_wheel(self, event):
        """Called whenever mouse wheel activated in canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        self._process_mouse_event(mouse_wheel_callbacks, event)

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
        bottom_right = self._map_canvas2world(self._scene_canvas.size)
        return np.array([top_left, bottom_right])

    def on_draw(self, _event: DrawEvent) -> None:
        """Called whenever the canvas is drawn.

        This is triggered from vispy whenever new data is sent to the canvas or
        the camera is moved and is connected in the `QtViewer`.
        """
        # The canvas corners in full world coordinates (i.e. across all layers).
        canvas_corners_world = self._canvas_corners_in_world
        for layer in self.viewer.layers:
            if layer.ndim <= 2:
                layer._update_draw(
                    scale_factor=1 / self.viewer.camera.zoom,
                    corner_pixels_displayed=canvas_corners_world[:, -layer.ndim :],
                    shape_threshold=self._scene_canvas.size,
                )

    def on_resize(self, event: ResizeEvent) -> None:
        """Called whenever canvas is resized."""
        self.viewer._canvas_size = self.size

    def add_layer_visual_mapping(self, napari_layer: Layer, vispy_layer: VispyBaseLayer) -> None:
        """Maps a napari layer to its corresponding vispy layer and sets the parent scene of the vispy layer.

        Parameters
        ----------
        napari_layer :
            Any napari layer, the layer type is the same as the vispy layer.
        vispy_layer :
            Any vispy layer, the layer type is the same as the napari layer.

        Returns
        -------
        None
        """

        vispy_layer.node.parent = self.view.scene
        self.layer_to_visual[napari_layer] = vispy_layer
        napari_layer.events.visible.connect(self._reorder_layers)
        # self.viewer.camera.events.angles.connect(vispy_layer._on_camera_move)
        self._reorder_layers()

    def _remove_layer(self, event):
        """When a layer is removed, remove its parent."""
        layer = event.value
        layer.events.visible.disconnect(self._reorder_layers)
        vispy_layer = self.layer_to_visual[layer]
        self.viewer.camera.events.disconnect(vispy_layer._on_camera_move)
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

        self._scene_canvas._draw_order.clear()
        self._scene_canvas.update()

    def _add_overlay_to_visual(self, overlay: Overlay) -> None:
        """Create vispy overlay and add to dictionary of overlay visuals"""
        vispy_overlay = create_vispy_overlay(overlay=overlay, viewer=self.viewer)
        if isinstance(overlay, CanvasOverlay):
            vispy_overlay.node.parent = self.view
        elif isinstance(overlay, SceneOverlay):
            vispy_overlay.node.parent = self.view.scene
        self._overlay_to_visual[overlay] = vispy_overlay

    def screenshot(self) -> QImage:
        """Return a QImage based on what is shown in the viewer."""
        return self.native.grabFramebuffer()
