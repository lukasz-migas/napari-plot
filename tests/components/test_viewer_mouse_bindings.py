"""Tests for the viewer zoom/selection mouse bindings."""

from types import SimpleNamespace

import numpy as np
import pytest

from napari_plot.components._viewer_mouse_bindings import (
    _get_auto_shape,
    box_zoom_auto,
    box_zoom_auto_trigger,
    box_zoom_box,
    box_zoom_horz,
    box_zoom_vert,
)
from napari_plot.components.dragtool import DragMode
from napari_plot.components.tools import Shape
from napari_plot.components.viewer_model import ViewerModel


@pytest.mark.parametrize(
    ("pos", "expected"),
    [
        ((105, 105), Shape.BOX),  # too small to decide
        ((200, 105), Shape.VERTICAL),  # wide and flat
        ((105, 200), Shape.HORIZONTAL),  # tall and thin
        ((130, 130), Shape.BOX),
        ((40, 160), Shape.BOX),
    ],
)
def test_get_auto_shape(pos, expected) -> None:
    """Shape is determined from the on-screen size of the drag."""
    assert _get_auto_shape(np.asarray([100, 100]), np.asarray(pos)) == expected


def _make_viewer(mode: DragMode) -> tuple[ViewerModel, list]:
    viewer = ViewerModel()
    viewer.drag_tool.active = mode
    viewer.camera.rect = (0.0, 10.0, 0.0, 10.0)
    spans = []
    viewer.events.span.connect(lambda emitted: spans.append(np.asarray(emitted.position).copy()))
    return viewer, spans


def _drag(func, viewer: ViewerModel, modifiers: tuple, release_pos=(0.0, 0.0)) -> None:
    """Drive mouse binding through press, move and release."""
    event = SimpleNamespace(type="mouse_press", modifiers=modifiers, pos=np.asarray([0.0, 0.0]))
    generator = func(viewer, event)
    next(generator)
    event.type = "mouse_move"
    event.pos = np.asarray(release_pos)
    next(generator)
    viewer.drag_tool.tool.position = (2.0, 4.0, 3.0, 6.0)
    event.type = "mouse_release"
    with pytest.raises(StopIteration):
        next(generator)


@pytest.mark.parametrize(
    ("func", "mode", "modifier", "attr", "expected"),
    [
        (box_zoom_horz, DragMode.HORIZONTAL_SPAN, "Shift", "shift", (0.0, 10.0, 3.0, 6.0)),
        (box_zoom_vert, DragMode.VERTICAL_SPAN, "Control", "ctrl", (2.0, 4.0, 0.0, 10.0)),
        (box_zoom_box, DragMode.BOX, "Alt", "alt", (2.0, 4.0, 3.0, 6.0)),
    ],
)
def test_box_zoom_shape_modifier_range(func, mode, modifier, attr, expected) -> None:
    """Modifier range and span event respect the shape of the tool."""
    viewer, spans = _make_viewer(mode)
    _drag(func, viewer, (modifier,))

    np.testing.assert_allclose(getattr(viewer.drag_tool, attr), expected)
    np.testing.assert_allclose(spans, [expected])


@pytest.mark.parametrize(
    ("release_pos", "shape", "expected"),
    [
        ((100.0, 5.0), Shape.VERTICAL, (2.0, 4.0, 0.0, 10.0)),
        ((5.0, 100.0), Shape.HORIZONTAL, (0.0, 10.0, 3.0, 6.0)),
        ((50.0, 50.0), Shape.BOX, (2.0, 4.0, 3.0, 6.0)),
    ],
)
def test_box_zoom_auto_trigger(release_pos, shape, expected) -> None:
    """Auto-trigger picks shape from the drag and emits shape-aware range."""
    viewer, spans = _make_viewer(DragMode.AUTO_TRIGGER)
    _drag(box_zoom_auto_trigger, viewer, ("Control",), release_pos)

    assert viewer.drag_tool.tool.shape == shape
    assert viewer.drag_tool.selection_active
    np.testing.assert_allclose(viewer.drag_tool.ctrl, expected)
    np.testing.assert_allclose(spans, [expected])

    # without modifiers, selection is not active
    _drag(box_zoom_auto_trigger, viewer, (), release_pos)
    assert not viewer.drag_tool.selection_active


def test_box_zoom_auto_modifier_overrides_shape() -> None:
    """Modifiers force the shape in auto mode."""
    viewer, spans = _make_viewer(DragMode.AUTO)
    _drag(box_zoom_auto, viewer, ("Shift",), (50.0, 50.0))

    assert viewer.drag_tool.tool.shape == Shape.HORIZONTAL
    np.testing.assert_allclose(spans, [(0.0, 10.0, 3.0, 6.0)])


def test_tool_change_resets_selection_active() -> None:
    """Flag set by auto-trigger does not leak into other tools."""
    viewer = ViewerModel()
    viewer.drag_tool.active = DragMode.AUTO_TRIGGER
    viewer.drag_tool.selection_active = True
    viewer.drag_tool.active = DragMode.AUTO
    assert not viewer.drag_tool.selection_active
