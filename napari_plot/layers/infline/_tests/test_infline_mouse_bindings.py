"""Test regions mouse bindings."""

import collections

import numpy as np
import pytest
from napari.utils._proxies import ReadOnlyWrapper
from napari.utils.interactions import (
    mouse_move_callbacks,
    mouse_press_callbacks,
    mouse_release_callbacks,
)

from napari_plot.layers import InfLine
from napari_plot.layers.infline._infline_constants import Mode, Orientation


@pytest.fixture
def Event():
    """Create a subclass for simulating vispy mouse events.

    Returns
    -------
    Event : Type
        A new tuple subclass named Event that can be used to create a
        NamedTuple object with fields "type", "is_dragging", and "modifiers".
    """
    return collections.namedtuple("Event", field_names=["type", "is_dragging", "modifiers", "position", "pos"])


def _get_position(pos: float):
    return 50, pos


@pytest.fixture
def create_known_infline_layer():
    """Create region layer with known coordinates

    Returns
    -------
    data : list
        List containing data used to generate regions.
    layer : napari_plot.layers.InfLine
        Region layer.
    n_inflines : int
        Number of inflines in the InfLine layer
    known_non_infline : list
        Data coordinates that are known to contain no region. Useful during
        testing when needing to guarantee no region is clicked on.
    """

    data = [
        (25, "vertical"),
        (500, "horizontal"),
        (85, "vertical"),
    ]
    known_non_infline = [0]
    n_inflines = len(data)

    layer = InfLine(data)
    assert layer.ndim == 2
    assert len(layer.data) == n_inflines
    assert len(layer.orientation) == n_inflines
    assert len(layer.selected_data) == 0

    return data, layer, n_inflines, known_non_infline


def test_add_infline_vertical(create_known_infline_layer, Event):
    """Add new region by clicking in add mode."""
    data, layer, n_inflines, known_non_infline = create_known_infline_layer
    layer.mode = "add"

    # Simulate click
    event = ReadOnlyWrapper(
        Event(
            type="mouse_press",
            is_dragging=False,
            modifiers=[],
            pos=np.asarray(known_non_infline),
            position=known_non_infline,
        )
    )
    mouse_press_callbacks(layer, event)

    known_non_infline_end = [0, 100]
    # Simulate drag end
    event = ReadOnlyWrapper(
        Event(
            type="mouse_move",
            is_dragging=True,
            modifiers=[],
            pos=np.asarray(known_non_infline_end),
            position=known_non_infline_end,
        )
    )
    mouse_move_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        Event(
            type="mouse_release",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=known_non_infline_end,
        )
    )
    mouse_release_callbacks(layer, event)

    # Check new shape added at coordinates
    assert len(layer.data) == n_inflines + 1
    assert layer.orientation[-1] == Orientation.VERTICAL


def test_add_infline_vertical_force_horizontal(create_known_infline_layer, Event):
    """Add new region by clicking in add mode."""
    data, layer, n_inflines, known_non_infline = create_known_infline_layer
    layer.mode = "add"

    # Simulate click
    event = ReadOnlyWrapper(
        Event(
            type="mouse_press",
            is_dragging=False,
            modifiers=[],
            pos=np.asarray(known_non_infline),
            position=known_non_infline,
        )
    )
    mouse_press_callbacks(layer, event)

    known_non_infline_end = [0, 100]
    # Simulate drag end
    event = ReadOnlyWrapper(
        Event(
            type="mouse_move",
            is_dragging=True,
            modifiers=["Shift"],
            pos=np.asarray(known_non_infline_end),
            position=known_non_infline_end,
        )
    )
    mouse_move_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        Event(
            type="mouse_release",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=known_non_infline_end,
        )
    )
    mouse_release_callbacks(layer, event)

    # Check new shape added at coordinates
    assert len(layer.data) == n_inflines + 1
    assert layer.orientation[-1] == Orientation.HORIZONTAL


def test_add_infline_horizontal(create_known_infline_layer, Event):
    """Add new region by clicking in add mode."""
    data, layer, n_inflines, known_non_infline = create_known_infline_layer
    layer.mode = "add"

    # Simulate click
    event = ReadOnlyWrapper(
        Event(
            type="mouse_press",
            is_dragging=False,
            modifiers=[],
            pos=np.asarray(known_non_infline),
            position=known_non_infline,
        )
    )
    mouse_press_callbacks(layer, event)

    known_non_infline_end = [100, 0]
    # Simulate drag end
    event = ReadOnlyWrapper(
        Event(
            type="mouse_move",
            is_dragging=True,
            modifiers=[],
            pos=np.asarray(known_non_infline_end),
            position=known_non_infline_end,
        )
    )
    mouse_move_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        Event(
            type="mouse_release",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=known_non_infline_end,
        )
    )
    mouse_release_callbacks(layer, event)

    # Check new shape added at coordinates
    assert len(layer.data) == n_inflines + 1
    assert layer.orientation[-1] == Orientation.HORIZONTAL


def test_add_infline_horizontal_force_vertical(create_known_infline_layer, Event):
    """Add new region by clicking in add mode."""
    data, layer, n_inflines, known_non_infline = create_known_infline_layer
    layer.mode = "add"

    # Simulate click
    event = ReadOnlyWrapper(
        Event(
            type="mouse_press",
            is_dragging=False,
            modifiers=[],
            pos=np.asarray(known_non_infline),
            position=known_non_infline,
        )
    )
    mouse_press_callbacks(layer, event)

    known_non_infline_end = [100, 0]
    # Simulate drag end
    event = ReadOnlyWrapper(
        Event(
            type="mouse_move",
            is_dragging=True,
            modifiers=["Control"],
            pos=np.asarray(known_non_infline_end),
            position=known_non_infline_end,
        )
    )
    mouse_move_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        Event(
            type="mouse_release",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=known_non_infline_end,
        )
    )
    mouse_release_callbacks(layer, event)

    # Check new shape added at coordinates
    assert len(layer.data) == n_inflines + 1
    assert layer.orientation[-1] == Orientation.VERTICAL


def test_not_adding_or_selecting_infline(create_known_infline_layer, Event):
    """Don't add or select a shape by clicking on one in pan_zoom mode."""
    data, layer, n_inflines, _ = create_known_infline_layer
    layer.mode = "pan_zoom"

    # Simulate click
    event = ReadOnlyWrapper(
        Event(
            type="mouse_press",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=(0, 0),
        )
    )
    mouse_press_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        Event(
            type="mouse_release",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=(0, 0),
        )
    )
    mouse_release_callbacks(layer, event)

    # Check no new shape added and non selected
    assert len(layer.data) == n_inflines
    assert len(layer.selected_data) == 0


def test_select_infline(create_known_infline_layer, Event):
    """Select a shape by clicking on one in select mode."""
    data, layer, n_inflines, _ = create_known_infline_layer

    layer.mode = "select"
    position = _get_position(data[0][0])

    # Simulate click
    event = ReadOnlyWrapper(
        Event(
            type="mouse_press",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=position,
        )
    )
    mouse_press_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        Event(
            type="mouse_release",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=position,
        )
    )
    mouse_release_callbacks(layer, event)

    # Check clicked shape selected
    assert len(layer.selected_data) == 1
    assert layer.selected_data == {0}


@pytest.mark.parametrize(
    "mode",
    [
        "select",
        "move",
        "add",
    ],
)
def test_after_in_add_mode_infline(mode, create_known_infline_layer, Event):
    """Don't add or select a shape by clicking on one in pan_zoom mode."""
    data, layer, n_inflines, _ = create_known_infline_layer

    layer.mode = mode
    layer.mode = "pan_zoom"
    position = _get_position(data[0][0])

    # Simulate click
    event = ReadOnlyWrapper(
        Event(
            type="mouse_press",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=position,
        )
    )
    mouse_press_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        Event(
            type="mouse_release",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=position,
        )
    )
    mouse_release_callbacks(layer, event)

    # Check no new shape added and non selected
    assert len(layer.data) == n_inflines
    assert len(layer.selected_data) == 0


def test_unselect_select_infline(create_known_infline_layer, Event):
    """Select a shape by clicking on one in select mode."""
    data, layer, n_inflines, _ = create_known_infline_layer

    layer.mode = "select"
    position = _get_position(data[0][0])
    layer.selected_data = {1}

    # Simulate click
    event = ReadOnlyWrapper(
        Event(
            type="mouse_press",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=position,
        )
    )
    mouse_press_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        Event(
            type="mouse_release",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=position,
        )
    )
    mouse_release_callbacks(layer, event)

    # Check clicked shape selected
    assert len(layer.selected_data) == 1
    assert layer.selected_data == {0}


def test_not_selecting_infline(create_known_infline_layer, Event):
    """Don't select a shape by not clicking on one in select mode."""
    data, layer, n_inflines, known_non_infline = create_known_infline_layer

    layer.mode = "select"

    # Simulate click
    event = ReadOnlyWrapper(
        Event(
            type="mouse_press",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=known_non_infline,
        )
    )
    mouse_press_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        Event(
            type="mouse_release",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=known_non_infline,
        )
    )
    mouse_release_callbacks(layer, event)

    # Check clicked shape selected
    assert len(layer.selected_data) == 0


def test_unselecting_inflines(create_known_infline_layer, Event):
    """Unselect shapes by not clicking on one in select mode."""
    data, layer, n_inflines, known_non_infline = create_known_infline_layer

    layer.mode = "select"
    layer.selected_data = {0, 1}
    assert len(layer.selected_data) == 2

    # Simulate click
    event = ReadOnlyWrapper(
        Event(
            type="mouse_press",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=known_non_infline,
        )
    )
    mouse_press_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        Event(
            type="mouse_release",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=known_non_infline,
        )
    )
    mouse_release_callbacks(layer, event)

    # Check clicked shape selected
    assert len(layer.selected_data) == 0


def test_selecting_inflines_with_drag(create_known_infline_layer, Event):
    """Select all shapes when drag box includes all of them."""
    data, layer, n_inflines, known_non_infline = create_known_infline_layer

    layer.mode = "select"

    # Simulate click
    event = ReadOnlyWrapper(
        Event(
            type="mouse_press",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=known_non_infline,
        )
    )
    mouse_press_callbacks(layer, event)

    # Simulate drag start
    event = ReadOnlyWrapper(
        Event(
            type="mouse_move",
            is_dragging=True,
            modifiers=[],
            pos=(),
            position=known_non_infline,
        )
    )
    mouse_move_callbacks(layer, event)

    # Simulate drag end
    event = ReadOnlyWrapper(
        Event(
            type="mouse_move",
            is_dragging=True,
            modifiers=[],
            pos=(),
            position=(1000, 1000),
        )
    )
    mouse_move_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        Event(
            type="mouse_release",
            is_dragging=True,
            modifiers=[],
            pos=(),
            position=(1000, 1000),
        )
    )
    mouse_release_callbacks(layer, event)

    # Check all shapes selected as drag box contains them
    assert len(layer.selected_data) == n_inflines


def test_selecting_no_inflines_with_drag(create_known_infline_layer, Event):
    """Select all shapes when drag box includes all of them."""
    data, layer, n_inflines, known_non_infline = create_known_infline_layer

    layer.mode = "select"

    # Simulate click
    event = ReadOnlyWrapper(
        Event(
            type="mouse_press",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=known_non_infline,
        )
    )
    mouse_press_callbacks(layer, event)

    # Simulate drag start
    event = ReadOnlyWrapper(
        Event(
            type="mouse_move",
            is_dragging=True,
            modifiers=[],
            pos=(),
            position=known_non_infline,
        )
    )
    mouse_move_callbacks(layer, event)

    # Simulate drag end
    event = ReadOnlyWrapper(
        Event(
            type="mouse_move",
            is_dragging=True,
            modifiers=[],
            pos=(),
            position=(200, 20),
        )
    )
    mouse_move_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        Event(
            type="mouse_release",
            is_dragging=True,
            modifiers=[],
            pos=(),
            position=(200, 20),
        )
    )
    mouse_release_callbacks(layer, event)

    # Check no shapes selected as drag box doesn't contain them
    assert len(layer.selected_data) == 0


@pytest.mark.parametrize("attr", ["_move_modes", "_drag_modes", "_cursor_modes"])
def test_all_modes_covered(attr):
    """
    Test that all dictionaries modes have all the keys, this simplify the handling logic
    As we do not need to test whether a key is in a dict or not.
    """
    mode_dict = getattr(InfLine, attr)
    assert {k.value for k in mode_dict} == set(Mode.keys())
