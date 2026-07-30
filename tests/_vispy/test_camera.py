"""Tests for plot-specific VisPy camera interactions."""

from types import SimpleNamespace

import numpy as np
import pytest

from napari_plot._vispy.components.camera import LimitedPanZoomCamera, make_rect
from napari_plot.components._viewer_mouse_bindings import box_zoom_box
from napari_plot.components.dragtool import DragMode
from napari_plot.components.viewer_model import ViewerModel


class _Transform:
    """Minimal transform that maps two-dimensional positions unchanged."""

    @staticmethod
    def imap(position):
        return np.asarray([position[0], position[1], 0.0, 0.0])


class _CameraHarness:
    """Minimal camera state required by the release-event handler."""

    interactive = True
    extent = None
    extent_mode = "unrestricted"
    _check_range = LimitedPanZoomCamera._check_range
    _make_zoom_rect = LimitedPanZoomCamera._make_zoom_rect

    def __init__(self, viewer: ViewerModel) -> None:
        self.viewer = viewer
        self._transform = _Transform()
        self._rect = make_rect(0.0, 10.0, 0.0, 10.0)

    @property
    def rect(self):
        """Return the current camera rectangle."""
        return self._rect

    @rect.setter
    def rect(self, value) -> None:
        self._rect = value


@pytest.mark.parametrize("mode", [DragMode.AUTO, DragMode.BOX])
def test_left_mouse_release_completes_drag_zoom(mode: DragMode) -> None:
    """VisPy 0.16 reports the released button outside ``buttons``."""
    viewer = ViewerModel()
    viewer.drag_tool.active = mode
    camera = _CameraHarness(viewer)
    event = SimpleNamespace(
        handled=False,
        type="mouse_release",
        button=1,
        buttons=[],
        pos=(4.0, 6.0),
        press_event=SimpleNamespace(pos=(1.0, 2.0)),
        mouse_event=SimpleNamespace(modifiers=()),
    )

    LimitedPanZoomCamera.viewbox_mouse_event(camera, event)

    assert camera.rect.left == 1.0
    assert camera.rect.right == 4.0
    assert camera.rect.bottom == 2.0
    assert camera.rect.top == 6.0


def test_box_zoom_emits_position_before_reset() -> None:
    """The span event contains the completed box rather than reset values."""
    viewer = ViewerModel()
    viewer.drag_tool.active = DragMode.BOX
    event = SimpleNamespace(type="mouse_press", modifiers=())
    spans = []
    viewer.events.span.connect(lambda emitted: spans.append(emitted.position.copy()))

    generator = box_zoom_box(viewer, event)
    next(generator)
    viewer.drag_tool.tool.position = (1.0, 4.0, 2.0, 6.0)
    event.type = "mouse_release"

    with pytest.raises(StopIteration):
        next(generator)

    np.testing.assert_allclose(spans, [[1.0, 4.0, 2.0, 6.0]])
    np.testing.assert_allclose(viewer.drag_tool.tool.position, [0.0, 0.0, 0.0, 0.0])
