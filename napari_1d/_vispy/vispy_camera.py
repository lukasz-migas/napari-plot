"""Camera model"""
import typing as ty

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

        # Create camera
        self._view.camera = LimitedPanZoomCamera(self._viewer)
        self._view.camera.viewbox_key_event = viewbox_key_event

        # connect events
        self._camera.events.rect.connect(self._on_rect_change)
        self._camera.events.axis_mode.connect(self._on_axis_mode_change)
        self._camera.events.extent.connect(self._on_extent_change)
        self._camera.events.extent_mode.connect(self._on_extent_mode_change)

        self._on_axis_mode_change(None)
        self._on_extent_mode_change(None)
        self._on_rect_change(None)

    @property
    def camera(self):
        """Return camera instance."""
        return self._view.camera

    @property
    def rect(self):
        """Get rect"""
        rect = self.camera.rect
        return rect.left, rect.right, rect.bottom, rect.top

    @rect.setter
    def rect(self, rect):
        if self.rect == rect:
            return
        _rect = Rect(self.camera.rect)
        _rect.left, _rect.right, _rect.bottom, _rect.top = rect  # nicely unpack tuple
        self.camera.rect = _rect

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

    def _on_rect_change(self, event):
        self.rect = self._camera.rect

    def _on_extent_change(self, event):
        self.extent = self._camera.extent

    def _on_axis_mode_change(self, event):
        self.camera.axis_mode = self._camera.extent

    def _on_extent_mode_change(self, event):
        self.camera.extent_mode = self._camera.extent
        self._on_extent_change(None)

    def on_draw(self, event):
        """Called whenever the canvas is drawn.

        Update camera model rect.
        """
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
