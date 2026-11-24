"""Test editing through the mouse callbacks installed by the layer modes."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event, current_thread
from types import SimpleNamespace

import numpy as np
import pytest
from napari.layers.base import Layer
from napari.utils._proxies import ReadOnlyWrapper
from napari.utils.interactions import mouse_move_callbacks, mouse_press_callbacks, mouse_release_callbacks

from napari_plot.layers import Rectangles, Scatter, Text


def _drag(
    layer: Layer,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    modifiers: tuple[str, ...] = (),
    plot_selection_tool: bool = False,
) -> None:
    path = [(mouse_press_callbacks, "mouse_press", start)]
    if start != end:
        path.append((mouse_move_callbacks, "mouse_move", end))
    path.append((mouse_release_callbacks, "mouse_release", end))
    for callback, event_type, position in path:
        event = SimpleNamespace(
            type=event_type,
            button=1,
            handled=False,
            modifiers=modifiers,
            pos=np.asarray(position[::-1]) * 10,
            position=position,
            is_dragging=event_type == "mouse_move",
            view_direction=None,
            dims_displayed=[0, 1],
            plot_selection_tool=plot_selection_tool,
        )
        callback(layer, ReadOnlyWrapper(event, exceptions=("handled",)))


def test_scatter_can_add_select_and_remove_points() -> None:
    """Scatter's edit modes reuse point selection, data and feature updates."""
    layer = Scatter([[10, 10]], size=1, scaling=True, features={"sample": [1]})
    layer.mode = "add"
    assert not layer.mouse_pan
    _drag(layer, (5, 2), (5, 2))
    _drag(layer, (7, 2), (7, 2), plot_selection_tool=True)
    np.testing.assert_array_equal(layer.data, [[10, 10], [5, 2]])

    layer.mode = "select"
    _drag(layer, (10, 10), (10, 10))
    assert set(layer.selected_data) == {0}
    layer.remove_selected()
    np.testing.assert_array_equal(layer.data, [[5, 2]])
    assert len(layer.features) == 1


def test_fixed_size_scatter_status_during_add(monkeypatch: pytest.MonkeyPatch) -> None:
    """A status read can overlap a click that changes the number of visible points."""
    layer = Scatter([[1.1, 1.2], [2.0, 2.1]], size=12, scaling=False)
    layer._update_draw(0.01, np.array([[0.0, 0.0], [3.5, 9.0]]), (900, 350))
    layer.mode = "add"
    reading = Event()
    added = Event()
    edit_thread = current_thread()
    original_ix = np.ix_

    def pause_view_read(*indices: np.ndarray) -> tuple[np.ndarray, ...]:
        result = original_ix(*indices)
        if current_thread() is not edit_thread and not reading.is_set():
            reading.set()
            assert added.wait(timeout=5)
        return result

    monkeypatch.setattr(np, "ix_", pause_view_read)
    position = (1.4, 3.3)
    with ThreadPoolExecutor(max_workers=1) as executor:
        status = executor.submit(layer.get_status, position, world=True, dims_displayed=[0, 1])
        try:
            assert reading.wait(timeout=5)
            _drag(layer, position, position)
        finally:
            added.set()
        status.result(timeout=5)

    assert layer.get_value(position, world=True) == 2


@pytest.mark.parametrize("modifier", ["Shift", "Control"])
def test_fixed_size_scatter_drag_selects_visible_centers(modifier: str) -> None:
    """The drag box uses visible centers in layer coordinates and toggles with modifiers."""
    layer = Scatter(
        [[1.0, 1.0], [0.75, 1.0], [1.125, 1.125], [1.0, 1.275]],
        size=12,
        scaling=False,
        translate=(4.0, 2.0),
        shown=[True, True, False, True],
    )
    layer._update_draw(0.01, np.array([[0.0, 0.0], [8.0, 6.0]]), (600, 800))
    layer.mode = "select"
    start, end = (5.25, 3.25), (4.75, 2.75)
    _drag(layer, start, end)
    assert set(layer.selected_data) == {0, 1}
    assert layer._highlight_box is None

    layer.selected_data = {0, 3}
    _drag(layer, start, end, modifiers=(modifier,))
    assert set(layer.selected_data) == {1, 3}


def test_rectangle_add_move_and_resize_preserve_existing_attributes() -> None:
    """An add drag creates data and edit drags preserve existing per-item style."""
    layer = Rectangles([[10, 10, 2, 2]], text=["existing"], translate=(4, 2))
    layer.mode = "add"
    _drag(layer, (6, 4), (10, 8))
    np.testing.assert_allclose(layer.data, [[10, 10, 2, 2], [4, 4, 4, 4]])
    np.testing.assert_equal(layer.text, ["existing", ""])

    layer.mode = "edit"
    _drag(layer, (8, 6), (9, 8))
    _drag(layer, (11, 10), (13, 11), modifiers=("Shift",))
    np.testing.assert_allclose(layer.data, [[10, 10, 2, 2], [6.5, 6, 6, 5]])
    np.testing.assert_equal(layer.text, ["existing", ""])


def test_text_drag_uses_screen_offset_and_preserves_labels() -> None:
    """Dragging a label moves its anchor while keeping its text and pixel offset."""
    layer = Text([[5, 5], [8, 8]], ["A", "B"], size=10, alignment="center", pixel_offset=(20, 0))
    layer._update_draw(0.1, [[10, 0], [0, 10]], (100, 100))
    layer.mode = "move"
    _drag(layer, (5, 7), (6, 9))
    np.testing.assert_allclose(layer.data, [[7, 6], [8, 8]])
    np.testing.assert_equal(layer.text, ["A", "B"])
    np.testing.assert_allclose(layer.pixel_offset, [[20, 0], [20, 0]])
