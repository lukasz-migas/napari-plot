"""Interaction tool."""
import typing as ty

from .vispy_box_visual import VispyBoxVisual

if ty.TYPE_CHECKING:
    from ..components.camera import Camera
    from ..components.viewer_model import ViewerModel


class VispyTool:
    """Interaction tool."""

    def __init__(self, view, camera: "Camera", viewer: "ViewerModel"):
        self._view = view
        self._camera = camera
        self._viewer = viewer

        self._box = VispyBoxVisual(viewer, parent=view, order=1e5)
        self._lasso = None
        self._polygon = None
        self.tool = self._box
