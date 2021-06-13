"""Camera model"""
import numpy as np
from vispy.geometry import Rect

from .camera import LimitedPanZoomCamera


class VispyCamera:
    """Vispy camera for both 2D and 3D rendering.

    Parameters
    ----------
    view : vispy.scene.widgets.viewbox.ViewBox
        Viewbox for current scene.
    camera : napari.components.Camera
        napari camera model.
    dims : napari.components.Dims
        napari dims model.
    viewer :
        instance of the viewer class

    """

    def __init__(self, view, camera, dims, viewer):
        self._view = view
        self._camera = camera
        self._dims = dims
        self._viewer = viewer

        # Create 2D camera
        self._2D_camera = LimitedPanZoomCamera(self._viewer)
        self._2D_camera.viewbox_key_event = viewbox_key_event

        # connect events
        self._dims.events.ndisplay.connect(self._on_ndisplay_change, position="first")
        self._camera.events.rect.connect(self._on_rect_change)
        self._camera.events.extent.connect(self._on_extent_change)
        self._camera.events.center.connect(self._on_center_change)
        self._camera.events.zoom.connect(self._on_zoom_change)
        self._camera.events.angles.connect(self._on_angles_change)

        self._on_ndisplay_change(None)

    @property
    def camera(self):
        """Return camera instance."""
        return self._2D_camera

    @property
    def angles(self):
        """3-tuple: Euler angles of camera in 3D viewing, in degrees."""
        return 0, 0, 90

    @angles.setter
    def angles(self, angles):
        if self.angles == tuple(angles):
            return

    @property
    def center(self):
        """tuple: Center point of camera view for 2D or 3D viewing."""
        # in 2D, we arbitrarily choose 0.0 as the center in z
        center = tuple(self._view.camera.center[:2]) + (0.0,)
        # switch from VisPy xyz ordering to NumPy prc ordering
        center = center[::-1]
        return center

    @center.setter
    def center(self, center):
        if self.center == tuple(center):
            return
        self._view.camera.center = center[::-1]
        self._view.camera.view_changed()

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
        self._on_center_change(None)
        self._on_zoom_change(None)
        self._on_angles_change(None)
        self._on_rect_change(None)

    def _on_rect_change(self, event):
        self.rect = self._camera.rect

    def _on_extent_change(self, event):
        self.extent = self._camera.extent

    def _on_center_change(self, event):
        self.center = self._camera.center[-self._dims.ndisplay :]

    def _on_zoom_change(self, event):
        self.zoom = self._camera.zoom

    def _on_angles_change(self, event):
        self.angles = self._camera.angles

    def on_draw(self, event):
        """Called whenever the canvas is drawn.

        Update camera model angles, center, and zoom.
        """
        with self._camera.events.angles.blocker(self._on_angles_change):
            self._camera.angles = self.angles
        with self._camera.events.center.blocker(self._on_center_change):
            self._camera.center = self.center
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
