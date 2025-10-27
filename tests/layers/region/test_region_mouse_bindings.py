"""Test regions mouse bindings."""

import numpy as np
import pytest
from napari.utils._proxies import ReadOnlyWrapper
from napari.utils.interactions import (
    mouse_move_callbacks,
    mouse_press_callbacks,
    mouse_release_callbacks,
)

from napari_plot.layers import Region
from napari_plot.layers.region.region import Mode, Orientation


def _get_position(pos):
    return 50, pos[1] - (pos[1] - pos[0]) / 2


@pytest.fixture
def create_known_region_layer():
    """Create region layer with known coordinates

    Returns
    -------
    data : list
        List containing data used to generate regions.
    layer : napari_plot.layers.Region
        Region layer.
    n_regions : int
        Number of regions in the region layer
    known_non_region : list
        Data coordinates that are known to contain no region. Useful during
        testing when needing to guarantee no region is clicked on.
    """
    data = [
        ([25, 50], "vertical"),
        ([500, 750], "horizontal"),
        ([80, 90], "vertical"),
    ]
    known_non_region = [0, 0]
    n_regions = len(data)

    layer = Region(data)
    assert layer.ndim == 2
    assert len(layer.data) == n_regions
    assert len(layer.selected_data) == 0

    return data, layer, n_regions, known_non_region


def test_add_region_vertical(create_known_region_layer, QtMouseEvent):
    """Add new region by clicking in add mode."""
    _data, layer, n_regions, known_non_region = create_known_region_layer
    layer.mode = "add"

    # Simulate click
    event = ReadOnlyWrapper(
        QtMouseEvent(
            type="mouse_press",
            is_dragging=False,
            modifiers=[],
            pos=np.asarray(known_non_region),
            position=known_non_region,
        )
    )
    mouse_press_callbacks(layer, event)

    known_non_region_end = [100, 0]
    # Simulate drag end
    event = ReadOnlyWrapper(
        QtMouseEvent(
            type="mouse_move",
            is_dragging=True,
            modifiers=[],
            pos=np.asarray(known_non_region_end),
            position=known_non_region_end,
        )
    )
    mouse_move_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        QtMouseEvent(
            type="mouse_release",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=known_non_region_end,
        )
    )
    mouse_release_callbacks(layer, event)

    # Check new shape added at coordinates
    assert len(layer.data) == n_regions + 1
    assert layer.orientation[-1] == Orientation.VERTICAL


def test_add_region_horizontal(create_known_region_layer, QtMouseEvent):
    """Add new region by clicking in add mode."""
    _data, layer, n_regions, known_non_region = create_known_region_layer
    layer.mode = "add"

    # Simulate click
    event = ReadOnlyWrapper(
        QtMouseEvent(
            type="mouse_press",
            is_dragging=False,
            modifiers=[],
            pos=np.asarray(known_non_region),
            position=known_non_region,
        )
    )
    mouse_press_callbacks(layer, event)

    known_non_region_end = [0, 100]
    # Simulate drag end
    event = ReadOnlyWrapper(
        QtMouseEvent(
            type="mouse_move",
            is_dragging=True,
            modifiers=[],
            pos=np.asarray(known_non_region_end),
            position=known_non_region_end,
        )
    )
    mouse_move_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        QtMouseEvent(
            type="mouse_release",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=known_non_region_end,
        )
    )
    mouse_release_callbacks(layer, event)

    # Check new shape added at coordinates
    assert len(layer.data) == n_regions + 1
    assert layer.orientation[-1] == Orientation.HORIZONTAL


def test_not_adding_or_selecting_region(create_known_region_layer, QtMouseEvent):
    """Don't add or select a shape by clicking on one in pan_zoom mode."""
    _data, layer, n_regions, _ = create_known_region_layer
    layer.mode = "pan_zoom"

    # Simulate click
    event = ReadOnlyWrapper(
        QtMouseEvent(
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
        QtMouseEvent(
            type="mouse_release",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=(0, 0),
        )
    )
    mouse_release_callbacks(layer, event)

    # Check no new shape added and non selected
    assert len(layer.data) == n_regions
    assert len(layer.selected_data) == 0


@pytest.mark.xfail(reason="Need to fix.")
def test_select_region(create_known_region_layer, QtMouseEvent):
    """Select a shape by clicking on one in select mode."""
    data, layer, _n_regions, _ = create_known_region_layer

    layer.mode = "select"
    position = _get_position(data[0][0])

    # Simulate click
    event = ReadOnlyWrapper(
        QtMouseEvent(
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
        QtMouseEvent(
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
def test_after_in_add_mode_region(mode, create_known_region_layer, QtMouseEvent):
    """Don't add or select a shape by clicking on one in pan_zoom mode."""
    data, layer, n_regions, _ = create_known_region_layer

    layer.mode = mode
    layer.mode = "pan_zoom"
    position = _get_position(data[0][0])

    # Simulate click
    event = ReadOnlyWrapper(
        QtMouseEvent(
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
        QtMouseEvent(
            type="mouse_release",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=position,
        )
    )
    mouse_release_callbacks(layer, event)

    # Check no new shape added and non selected
    assert len(layer.data) == n_regions
    assert len(layer.selected_data) == 0


@pytest.mark.xfail(reason="Need to fix.")
def test_unselect_select_region(create_known_region_layer, QtMouseEvent):
    """Select a shape by clicking on one in select mode."""
    data, layer, _n_regions, _ = create_known_region_layer

    layer.mode = "select"
    position = _get_position(data[0][0])
    layer.selected_data = {1}

    # Simulate click
    event = ReadOnlyWrapper(
        QtMouseEvent(
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
        QtMouseEvent(
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


def test_not_selecting_region(create_known_region_layer, QtMouseEvent):
    """Don't select a shape by not clicking on one in select mode."""
    _data, layer, _n_regions, known_non_region = create_known_region_layer

    layer.mode = "select"

    # Simulate click
    event = ReadOnlyWrapper(
        QtMouseEvent(
            type="mouse_press",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=known_non_region,
        )
    )
    mouse_press_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        QtMouseEvent(
            type="mouse_release",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=known_non_region,
        )
    )
    mouse_release_callbacks(layer, event)

    # Check clicked shape selected
    assert len(layer.selected_data) == 0


def test_unselecting_regions(create_known_region_layer, QtMouseEvent):
    """Unselect shapes by not clicking on one in select mode."""
    _data, layer, _n_regions, known_non_region = create_known_region_layer

    layer.mode = "select"
    layer.selected_data = {0, 1}
    assert len(layer.selected_data) == 2

    # Simulate click
    event = ReadOnlyWrapper(
        QtMouseEvent(
            type="mouse_press",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=known_non_region,
        )
    )
    mouse_press_callbacks(layer, event)

    # Simulate release
    event = ReadOnlyWrapper(
        QtMouseEvent(
            type="mouse_release",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=known_non_region,
        )
    )
    mouse_release_callbacks(layer, event)

    # Check clicked shape selected
    assert len(layer.selected_data) == 0


def test_selecting_regions_with_drag(create_known_region_layer, QtMouseEvent):
    """Select all shapes when drag box includes all of them."""
    _data, layer, n_regions, known_non_region = create_known_region_layer

    layer.mode = "select"

    # Simulate click
    event = ReadOnlyWrapper(
        QtMouseEvent(
            type="mouse_press",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=known_non_region,
        )
    )
    mouse_press_callbacks(layer, event)

    # Simulate drag start
    event = ReadOnlyWrapper(
        QtMouseEvent(
            type="mouse_move",
            is_dragging=True,
            modifiers=[],
            pos=(),
            position=known_non_region,
        )
    )
    mouse_move_callbacks(layer, event)

    # Simulate drag end
    event = ReadOnlyWrapper(
        QtMouseEvent(
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
        QtMouseEvent(
            type="mouse_release",
            is_dragging=True,
            modifiers=[],
            pos=(),
            position=(1000, 1000),
        )
    )
    mouse_release_callbacks(layer, event)

    # Check all shapes selected as drag box contains them
    assert len(layer.selected_data) == n_regions


def test_selecting_no_regions_with_drag(create_known_region_layer, QtMouseEvent):
    """Select all shapes when drag box includes all of them."""
    _data, layer, _n_regions, known_non_region = create_known_region_layer

    layer.mode = "select"

    # Simulate click
    event = ReadOnlyWrapper(
        QtMouseEvent(
            type="mouse_press",
            is_dragging=False,
            modifiers=[],
            pos=(),
            position=known_non_region,
        )
    )
    mouse_press_callbacks(layer, event)

    # Simulate drag start
    event = ReadOnlyWrapper(
        QtMouseEvent(
            type="mouse_move",
            is_dragging=True,
            modifiers=[],
            pos=(),
            position=known_non_region,
        )
    )
    mouse_move_callbacks(layer, event)

    # Simulate drag end
    event = ReadOnlyWrapper(
        QtMouseEvent(
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
        QtMouseEvent(
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
    mode_dict = getattr(Region, attr)
    assert {k.value for k in mode_dict} == set(Mode.keys())
