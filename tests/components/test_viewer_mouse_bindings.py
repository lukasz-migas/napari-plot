"""Tests for the viewer zoom/selection mouse bindings."""

from types import SimpleNamespace

import numpy as np
import pytest

from napari_plot.components._viewer_mouse_bindings import (
    _get_auto_shape,
    box_select,
    box_zoom_auto,
    box_zoom_auto_trigger,
    box_zoom_box,
    box_zoom_horz,
    box_zoom_vert,
    lasso_select,
    polygon_select,
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


def test_box_selection_publishes_geometry_and_layer_indices() -> None:
    """A box selects data in each selected visible layer with its own geometry."""
    viewer, spans = _make_viewer(DragMode.BOX_SELECT)
    scatter = viewer.add_scatter([[0, 0], [1, 1], [1, 1]], translate=(2, 1), shown=[True, True, False])
    line = viewer.add_line(np.array([[0, 0], [2, 3], [5, 6]]))
    multiline = viewer.add_multi_line({"x": np.array([0, 5]), "ys": [np.array([3, 3]), np.array([7, 7])]})
    bar = viewer.add_bar([[2, 8], [10, 8]])
    centroids = viewer.add_centroids([[2, 8], [10, 8]])
    hidden = viewer.add_scatter([[3, 2]], visible=False)
    other = viewer.add_scatter([[3, 2]])
    viewer.layers.selection = {scatter, line, multiline, bar, centroids, hidden}
    other.selected_data = {0}

    signals = []
    viewer.drag_tool.events.vertices.connect(lambda event: signals.append((event.type, event.value.copy())))
    viewer.events.selection.connect(lambda event: signals.append((event.type, event.value)))
    event = SimpleNamespace(type="mouse_press", button=1)
    drag = box_select(viewer, event)
    next(drag)
    viewer.drag_tool.tool.position = (1.5, 2.5, 2.5, 3.5)
    event.type = "mouse_release"
    with pytest.raises(StopIteration):
        next(drag)

    expected = {scatter: {1}, line: {1}, multiline: {0}, bar: {0}, centroids: {0}}
    assert signals[0][0] == "vertices"
    np.testing.assert_equal(signals[0][1], [[2.5, 1.5], [3.5, 1.5], [3.5, 2.5], [2.5, 2.5]])
    assert signals[1] == ("selection", expected)
    assert {layer: set(layer.selected_data) for layer in expected} == expected
    assert set(other.selected_data) == {0}
    assert not hidden.selected_data
    assert not spans


def test_box_selection_is_scoped_to_the_grid_cell() -> None:
    """The same data coordinates in another cell keep their selection."""
    viewer, _ = _make_viewer(DragMode.BOX_SELECT)
    viewer.add_scatter([[1, 1], [5, 5]])
    viewer.add_scatter([[1, 1], [5, 5]])
    viewer.layers.select_all()
    viewer.canvas.grid.enabled = True
    cell, [layer_index] = next(iter(viewer.canvas.grid.iter_viewboxes(viewer.layers)))
    target = viewer.layers[layer_index]
    other = viewer.layers[1 - layer_index]
    other.selected_data = {1}

    event = SimpleNamespace(type="mouse_press", button=1, viewbox=cell)
    drag = box_select(viewer, event)
    next(drag)
    viewer.drag_tool.tool.position = (0, 2, 0, 2)
    event.type = "mouse_release"
    with pytest.raises(StopIteration):
        next(drag)

    assert set(target.selected_data) == {0}
    assert set(other.selected_data) == {1}


@pytest.mark.parametrize(("binding", "mode"), [(polygon_select, DragMode.POLYGON), (lasso_select, DragMode.LASSO)])
def test_polygon_and_lasso_keep_vertices_and_support_cancellation(binding, mode: DragMode) -> None:
    """Polygon vertices keep their original order and right click clears the result."""
    viewer, spans = _make_viewer(mode)
    scatter = viewer.add_scatter([[1, 1], [5, 5]])
    points = [(0, 0), (3, 0), (3, 3), (0, 3)]
    if mode == DragMode.LASSO:
        event = SimpleNamespace(type="mouse_press", button=1, modifiers=(), position=points[0], pos=np.zeros(2))
        drag = binding(viewer, event)
        next(drag)
        event.type = "mouse_move"
        next(drag)
        for point in points[1:]:
            event.position = point
            event.pos = np.asarray(point) * 10
            next(drag)
        event.type = "mouse_release"
        with pytest.raises(StopIteration):
            next(drag)
    else:
        for point in points:
            _polygon_click(binding, viewer, point, button=1)

    np.testing.assert_equal(viewer.drag_tool.vertices, points)
    assert set(scatter.selected_data) == {0}
    _polygon_click(binding, viewer, points[-1], button=2)
    assert viewer.drag_tool.vertices.shape == (0, 2)
    assert not scatter.selected_data
    assert not spans


def _polygon_click(binding, viewer: ViewerModel, point: tuple[float, float], *, button: int) -> None:
    event = SimpleNamespace(type="mouse_press", button=button, modifiers=(), position=point, pos=np.asarray(point))
    drag = binding(viewer, event)
    next(drag)
    event.type = "mouse_release"
    with pytest.raises(StopIteration):
        next(drag)
