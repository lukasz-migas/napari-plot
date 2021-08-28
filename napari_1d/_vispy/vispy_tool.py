"""Interaction tool."""
import typing as ty

from .vispy_span_visual import VispyBoxVisual


if ty.TYPE_CHECKING:
    from ..components.camera import Camera
    from ..components.viewer_model import ViewerModel


class VispyTool:
    """Interaction tool."""

    def __init__(self, view, camera: "Camera", viewer: "ViewerModel"):
        self._view = view
        self._camera = camera
        self._viewer = viewer

        self._span = VispyBoxVisual(viewer, parent=view, order=1e5)
        self._box = None
        self.tool = self._span