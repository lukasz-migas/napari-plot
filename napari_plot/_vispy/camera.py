"""Camera model"""

import typing as ty

import numpy as np
from napari._vispy.camera import add_mouse_pan_zoom_toggles
from vispy.geometry import Rect

from napari_plot._vispy.components.camera import LimitedPanZoomCamera

if ty.TYPE_CHECKING:
    from napari_plot.components.camera import Camera
    from napari_plot.components.viewer_model import ViewerModel


class VispyCamera:
    """Vispy camera.

    Parameters
    ----------
    view : vispy.scene.widgets.viewbox.ViewBox
        Viewbox for current scene.
    camera : napari.components.Camera
        napari camera model.
    viewer :
        instance of the viewer class

    """

    def __init__(self, view, camera: "Camera", viewer: "ViewerModel"):
        self._view = view
        self._viewer = viewer
        self._camera = camera

        # Create camera
        self._view.camera = MouseToggledLimitedPanZoomCamera(viewer=self._viewer, aspect=camera.aspect)
        self._view.camera.viewbox_key_event = viewbox_key_event

        # connect events
        self._camera.events.mouse_pan.connect(self._on_mouse_toggles_change)
        self._camera.events.mouse_zoom.connect(self._on_mouse_toggles_change)
        self._camera.events.aspect.connect(self._on_aspect_change)
        self._camera.events.zoom.connect(self._on_zoom_change)
        self._camera.events.rect.connect(self._on_rect_change)
        self._camera.events.extent.connect(self._on_extent_change)
        self._camera.events.x_range.connect(self._on_range_change)
        self._camera.events.y_range.connect(self._on_range_change)
        self._camera.events.axis_mode.connect(self._on_axis_mode_change)
        self._camera.events.extent_mode.connect(self._on_extent_mode_change)
        self._camera.events.force_rect.connect(self._on_force_rect_change)

        self._on_axis_mode_change(None)
        self._on_extent_mode_change(None)
        self._on_rect_change(None)

    @property
    def camera(self):
        """Return camera instance."""
        return self._view.camera

    @property
    def zoom(self):
        """float: Scale from canvas pixels to world pixels."""
        canvas_size = np.array(self._view.canvas.size)
        scale = np.array([self._view.camera.rect.width, self._view.camera.rect.height])
        scale[np.isclose(scale, 0)] = 1  # fix for #2875
        zoom = np.min(canvas_size / scale)
        return zoom

    @zoom.setter
    def zoom(self, zoom):
        if self.zoom == zoom:
            return
        scale = np.array(self._view.canvas.size) / zoom
        # Set view rectangle, as left, right, width, height
        corner = np.subtract(self._view.camera.center[:2], scale / 2)
        self.rect = tuple(corner) + tuple(scale)

    @property
    def rect(self) -> ty.Tuple[float, float, float, float]:
        """Get rect"""
        rect = self.camera.rect
        return rect.left, rect.right, rect.bottom, rect.top

    @rect.setter
    def rect(self, rect: Rect):
        if self.rect == rect:
            return
        self._update_rect(rect)

    def _update_rect(self, rect: Rect) -> None:
        rect_obj = Rect(self.camera.rect)
        rect_obj.left, rect_obj.right, rect_obj.bottom, rect_obj.top = rect  # nicely unpack tuple
        self.camera.rect = rect_obj

    @property
    def extent(self):
        """Get rect"""
        return self.camera._extent

    @extent.setter
    def extent(self, extent):
        if self.extent == extent:
            return
        self.camera.extent = extent
        self.camera.set_default_state()
        self.camera.reset()
        self._on_rect_change(None)

    def _on_aspect_change(self):
        self.camera.aspect = self._camera.aspect

    def _on_mouse_toggles_change(self):
        self.mouse_pan = self._camera.mouse_pan
        self.camera.mouse_pan = self._camera.mouse_pan
        self.mouse_zoom = self._camera.mouse_zoom
        self.camera.mouse_zoom = self._camera.mouse_zoom

    def _on_zoom_change(self):
        self.zoom = self._camera.zoom

    def _on_rect_change(self, event):
        self.rect = self._camera.rect

    def _on_force_rect_change(self, event):
        self._update_rect(self._camera.rect)

    def _on_extent_change(self, event):
        self.extent = self._camera.get_effective_extent()

    def _on_range_change(self, event):
        self.extent = self._camera.get_effective_extent()
        self.camera.reset_view()

    def _on_axis_mode_change(self, event):
        self.camera.axis_mode = self._camera.axis_mode

    def _on_extent_mode_change(self, event):
        self.camera.extent_mode = self._camera.extent_mode
        self._on_extent_change(None)
        self.camera.reset_view()

    def on_draw(self, event):
        """Called whenever the canvas is drawn. Update camera model rect."""
        with self._camera.events.rect.blocker(self._on_rect_change):
            self._camera.rect = self.rect
        with self._camera.events.zoom.blocker(self._on_zoom_change):
            self._camera.zoom = self.zoom


def viewbox_key_event(event):
    """ViewBox key event handler.

    Parameters
    ----------
    event : vispy.util.event.Event
        The vispy event that triggered this method.
    """
    return


MouseToggledLimitedPanZoomCamera = add_mouse_pan_zoom_toggles(LimitedPanZoomCamera)
