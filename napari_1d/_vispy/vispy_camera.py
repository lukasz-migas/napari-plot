"""Camera model"""
import typing as ty

import numpy as np
from vispy.geometry import Rect

from .camera import LimitedPanZoomCamera

if ty.TYPE_CHECKING:
    from ..components.camera import Camera
    from ..components.viewer_model import ViewerModel


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
        self._camera = camera
        self._viewer = viewer

        # Create 2D camera
        self._2D_camera = LimitedPanZoomCamera(self._viewer)
        self._2D_camera.viewbox_key_event = viewbox_key_event

        # connect events
        self._camera.events.rect.connect(self._on_rect_change)
        self._camera.events.extent.connect(self._on_extent_change)
        self._camera.events.zoom.connect(self._on_zoom_change)

        self._on_ndisplay_change(None)

    @property
    def camera(self):
        """Return camera instance."""
        return self._2D_camera

    @property
    def zoom(self):
        """float: Scale from canvas pixels to world pixels."""
        canvas_size = np.min(self._view.canvas.size)
        scale = np.min([self._view.camera.rect.width, self._view.camera.rect.height])
        zoom = canvas_size / scale
        return zoom

    @zoom.setter
    def zoom(self, zoom):
        if self.zoom == zoom:
            return
        scale = np.min(self._view.canvas.size) / zoom
        # Set view rectangle, as left, right, width, height
        corner = np.subtract(self._view.camera.center[:2], scale / 2)
        self._view.camera.rect = tuple(corner) + (scale, scale)

    @property
    def rect(self):
        """Get rect"""
        rect = self._view.camera.rect
        return rect.left, rect.right, rect.bottom, rect.top

    @rect.setter
    def rect(self, rect):
        if self.rect == rect:
            return
        _rect = Rect(self._view.camera.rect)
        _rect.left = rect[0]
        _rect.right = rect[1]
        _rect.bottom = rect[2]
        _rect.top = rect[3]
        self._view.camera.rect = _rect

    @property
    def extent(self):
        """Get rect"""
        return self._view.camera._extents

    @extent.setter
    def extent(self, extent):
        if self.extent == extent:
            return
        self._view.camera.set_extents(*extent)
        self._view.camera.set_default_state()

    def _on_ndisplay_change(self, event):
        self._view.camera = self._2D_camera
        self._on_zoom_change(None)
        self._on_rect_change(None)

    def _on_rect_change(self, event):
        self.rect = self._camera.rect

    def _on_extent_change(self, event):
        self.extent = self._camera.extent

    def _on_zoom_change(self, event):
        self.zoom = self._camera.zoom

    def on_draw(self, event):
        """Called whenever the canvas is drawn.

        Update camera model angles, center, and zoom.
        """
        with self._camera.events.zoom.blocker(self._on_zoom_change):
            self._camera.zoom = self.zoom
        with self._camera.events.rect.blocker(self._on_rect_change):
            self._camera.rect = self.rect


def viewbox_key_event(event):
    """ViewBox key event handler.

    Parameters
    ----------
    event : vispy.util.event.Event
        The vispy event that triggered this method.
    """
    return
