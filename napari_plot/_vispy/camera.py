"""Camera model"""

from __future__ import annotations

import typing as ty

import numpy as np
from napari._vispy.camera import add_mouse_pan_zoom_toggles
from vispy.geometry import Rect

from napari_plot._vispy.components.camera import LimitedPanZoomCamera
from napari_plot.components.axis import transform_axis_values

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
    follow_model : bool
        When True, the camera starts from the model state without writing its own default state back, so adding a
        camera (e.g. for another plot cell in grid mode) does not reset the view of the others.

    """

    def __init__(self, view, camera: Camera, viewer: ViewerModel, follow_model: bool = False):
        self._view = view
        self._camera = camera
        self._viewer = viewer
        # rect last exchanged with the model; several cameras can follow one model (grid mode) and only the camera
        # whose rect changed since then may write it back
        self._synced_rect: tuple[float, float, float, float] | None = None
        self._applying = False
        self._initializing = follow_model

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
        # A cell added in grid mode must publish its new bounds before auto-zoom handlers read them.
        self._camera.events.zoomed.connect(self._on_sync_rect, position="first")

        self._on_axis_mode_change(None)
        self._on_extent_mode_change(None)
        self._initializing = False
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
        display_rect = (
            corner[0],
            corner[0] + scale[0],
            corner[1],
            corner[1] + scale[1],
        )
        self.rect = self._transform_rect(display_rect, inverse=True)

    def _transform_rect(
        self,
        rect: Rect | ty.Iterable[float],
        *,
        inverse: bool,
    ) -> tuple[float, float, float, float]:
        """Transform a camera rectangle between data and display coordinates."""
        values = (rect.left, rect.right, rect.bottom, rect.top) if isinstance(rect, Rect) else tuple(rect)
        xmin, xmax, ymin, ymax = values
        return (
            transform_axis_values(xmin, self._viewer.axis.x_scale, inverse=inverse),
            transform_axis_values(xmax, self._viewer.axis.x_scale, inverse=inverse),
            transform_axis_values(ymin, self._viewer.axis.y_scale, inverse=inverse),
            transform_axis_values(ymax, self._viewer.axis.y_scale, inverse=inverse),
        )

    @property
    def rect(self) -> tuple[float, float, float, float]:
        """Get rect"""
        rect = self.camera.rect
        return self._transform_rect(
            (rect.left, rect.right, rect.bottom, rect.top),
            inverse=True,
        )

    @rect.setter
    def rect(self, rect: Rect | ty.Iterable[float]):
        if self.rect == rect:
            return
        self._update_rect(rect)

    def _on_sync_rect(self, event: ty.Any) -> None:
        """Sync rect from the Camera object to the Camera model when this camera was changed."""
        if self._initializing or self._applying or self.rect == self._synced_rect:
            return
        self._sync_to_model()

    def _sync_to_model(self) -> None:
        """Write the rect of this camera to the Camera model."""
        self._synced_rect = self.rect
        with self._camera.events.rect.blocker(self._on_rect_change):
            self._camera.rect = self._synced_rect

    def _update_rect(self, rect: Rect | ty.Iterable[float]) -> None:
        display_rect = self._transform_rect(rect, inverse=False)
        rect_obj = Rect(self.camera.rect)
        rect_obj.left, rect_obj.right, rect_obj.bottom, rect_obj.top = display_rect
        previous = self.rect
        self._applying = True
        try:
            self.camera._set_rect(rect_obj, interactive=False)
        finally:
            self._applying = False
        self._synced_rect = self.rect
        # the camera can limit the rect, so the model gets the rect that is shown when it changed
        if self._synced_rect != previous:
            self._sync_to_model()

    @property
    def extent(self):
        """Get rect"""
        extent = self.camera._extent
        if extent is None:
            return None
        return self._transform_rect(
            (extent.left, extent.right, extent.bottom, extent.top),
            inverse=True,
        )

    @extent.setter
    def extent(self, extent):
        if self.extent == extent:
            return
        self.camera.extent = self._transform_rect(extent, inverse=False)
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
        if self.rect != self._camera.rect:
            self._sync_to_model()
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
