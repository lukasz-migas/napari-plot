"""Tests for plot-specific VisPy camera interactions."""

from types import SimpleNamespace

import numpy as np
import pytest
from pytestqt.qtbot import QtBot
from vispy.geometry import Rect
from vispy.scene import ViewBox

from napari_plot._vispy.camera import VispyCamera
from napari_plot._vispy.components.camera import LimitedPanZoomCamera, make_rect
from napari_plot.components._viewer_mouse_bindings import box_zoom_box
from napari_plot.components.axis import Axis
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
    _left_drag_pans = False
    _check_range = LimitedPanZoomCamera._check_range
    _make_zoom_rect = LimitedPanZoomCamera._make_zoom_rect
    _is_zoom_drag = LimitedPanZoomCamera._is_zoom_drag

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


def test_left_mouse_release_zooms_vertical_drag_for_horizontal_span() -> None:
    """A horizontal span dragged straight up/down still zooms the y-axis."""
    viewer = ViewerModel()
    viewer.drag_tool.active = DragMode.HORIZONTAL_SPAN
    camera = _CameraHarness(viewer)
    event = SimpleNamespace(
        handled=False,
        type="mouse_release",
        button=1,
        buttons=[],
        pos=(3.0, 8.0),
        press_event=SimpleNamespace(pos=(3.0, 2.0)),
        mouse_event=SimpleNamespace(modifiers=()),
    )

    LimitedPanZoomCamera.viewbox_mouse_event(camera, event)

    assert camera.rect.left == 0.0
    assert camera.rect.right == 10.0
    assert camera.rect.bottom == 2.0
    assert camera.rect.top == 8.0


def test_pan_zoom_with_drag_tool_disabled() -> None:
    """With no drag tool, either mouse button pans and the wheel zooms."""
    viewer = ViewerModel()
    viewer.drag_tool.active = DragMode.NONE
    layer = viewer.add_scatter([[1.0, 1.0]], scaling=False)
    vispy = VispyCamera(ViewBox(size=(100, 100)), viewer.camera, viewer)
    camera = vispy.camera
    viewer.camera.rect = (0.0, 10.0, 0.0, 10.0)
    layer.mode = "add"
    assert not camera.mouse_pan
    layer.mode = "pan_zoom"
    assert camera.mouse_pan

    press = SimpleNamespace(
        type="mouse_press",
        button=1,
        buttons=[1],
        pos=(30, 40),
        handled=False,
        mouse_event=SimpleNamespace(modifiers=("Shift",)),
    )
    move = SimpleNamespace(
        type="mouse_move",
        button=1,
        buttons=[1],
        pos=(60, 70),
        handled=False,
        press_event=press,
        last_event=press,
        mouse_event=press.mouse_event,
    )
    camera.viewbox_mouse_event(press)
    camera.viewbox_mouse_event(move)
    assert not press.handled
    assert not move.handled
    assert vispy.rect == pytest.approx((0.0, 10.0, 0.0, 10.0))

    press.mouse_event.modifiers = ()
    for button in (1, 2):
        viewer.camera.rect = (0.0, 10.0, 0.0, 10.0)
        press.button = move.button = button
        press.buttons = move.buttons = [button]
        press.handled = move.handled = False
        camera.viewbox_mouse_event(press)
        camera.viewbox_mouse_event(move)
        assert press.handled
        assert move.handled
        camera.viewbox_mouse_event(SimpleNamespace(type="mouse_release", button=button, handled=False))
        assert vispy.rect == pytest.approx((-3.0, 7.0, 3.0, 13.0))

    wheel = SimpleNamespace(type="mouse_wheel", pos=(50, 50), delta=(0, 1), handled=False)
    camera.viewbox_mouse_event(wheel)
    assert wheel.handled
    assert camera.rect.width < 10.0
    assert camera.rect.height < 10.0


def test_disabling_drag_tool_mid_gesture_cancels_left_drag() -> None:
    """A camera that already accepted a press can receive events after the tool is removed."""
    viewer = ViewerModel()
    viewer.drag_tool.active = DragMode.BOX
    vispy = VispyCamera(ViewBox(size=(100, 100)), viewer.camera, viewer)
    camera = vispy.camera
    before = vispy.rect
    press = SimpleNamespace(type="mouse_press", button=1, pos=(20, 30), handled=False)
    camera.viewbox_mouse_event(press)
    assert press.handled
    viewer.drag_tool.active = DragMode.NONE

    for event_type in ("mouse_move", "mouse_release"):
        event = SimpleNamespace(
            type=event_type,
            button=1,
            buttons=[1],
            pos=(60, 70),
            handled=False,
            press_event=press,
            mouse_event=SimpleNamespace(modifiers=()),
        )
        camera.viewbox_mouse_event(event)
        assert not event.handled
    assert vispy.rect == before


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


def test_transform_rect_for_log_axes() -> None:
    """Camera rectangles are transformed independently for each log axis."""
    camera = VispyCamera.__new__(VispyCamera)
    camera._viewer = SimpleNamespace(axis=Axis(x_scale="log", y_scale="linear"))
    data_rect = Rect(0.1, 2.0, 999.9, 3.0)

    display_rect = camera._transform_rect(data_rect, inverse=False)

    assert np.allclose(display_rect, (-1.0, 3.0, 2.0, 5.0))
    assert np.allclose(
        camera._transform_rect(display_rect, inverse=True),
        (0.1, 1000.0, 2.0, 5.0),
    )


@pytest.mark.parametrize("tiled", [False, True])
def test_auto_zoom_fits_small_values_with_bottom_lock(qtbot: QtBot, tiled: bool) -> None:
    """Refit y after a horizontal zoom without pinning it to a negative peak outside the window."""
    viewer = ViewerModel()
    viewer.camera.extent_mode = "restricted"
    viewer.camera.axis_mode = "lock_to_bottom"
    camera = VispyCamera(ViewBox(), viewer.camera, viewer)
    viewer.add_line([[655, -0.0025], [656, 0.000001], [660, 0.00003], [664.5, 0.0004], [665, 1]])
    zoomed = viewer.camera.events.zoomed

    def auto_zoom() -> None:
        with zoomed.blocker():
            viewer.reset_current_y_view()

    camera.camera.rect = make_rect(656, 665, 0, 1)
    assert camera.rect[2] == pytest.approx(viewer.camera.extent[2])

    zoomed.connect(auto_zoom)
    target = VispyCamera(ViewBox(), viewer.camera, viewer, follow_model=True) if tiled else camera
    target.camera.rect = make_rect(656, 664.5, 0, 1)
    assert camera.rect == pytest.approx((656, 664.5, 0, 0.00042))
    assert target.rect == pytest.approx(camera.rect)
    assert viewer.camera.rect == pytest.approx(camera.rect)


def test_grid_cell_camera_shares_only_configured_dimensions() -> None:
    viewer = ViewerModel()
    first = viewer.add_line([[1, 2], [10, 8]])
    second = viewer.add_line([[1, 50], [10, 80]])
    a = VispyCamera(ViewBox(), viewer.camera, viewer)
    b = VispyCamera(ViewBox(), viewer.camera, viewer, follow_model=True)
    settings = viewer.canvas.grid.cell(0, 1)
    settings.ylim = (85, 45)
    settings.x_scale = "log"
    a.configure_cell(None, [first], (True, False))
    b.configure_cell(settings, [second], (True, False))

    assert b.camera.flip == (False, True, False)
    assert a.rect[2:] == pytest.approx(viewer._get_rect_extent(layers=[first])[2:])
    assert b.rect[2:] == pytest.approx((45, 85))

    b.camera.rect = make_rect(np.log10(2), np.log10(6), 55, 75)
    assert a.rect[:2] == pytest.approx((2, 6))
    assert a.rect[2:] == pytest.approx(viewer._get_rect_extent(layers=[first])[2:])
    assert b.rect[2:] == pytest.approx((55, 75))
    assert b.reset_cell_axis("y")
    assert b.rect == pytest.approx((2, 6, 45, 85))
