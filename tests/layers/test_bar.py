"""Tests for the Bar layer."""

import numpy as np
import pytest

from napari_plot.layers import Bar
from napari_plot.layers.bar.bar import BarOrientation, _select_bar


def test_bar_accepts_values_or_position_value_rows() -> None:
    """One-dimensional input receives generated integer positions."""
    layer = Bar([2, 4, 1])
    np.testing.assert_array_equal(layer.data, [[0, 2], [1, 4], [2, 1]])

    layer.data = [[10, 3], [20, 5]]
    np.testing.assert_array_equal(layer.positions, [10, 20])
    np.testing.assert_array_equal(layer.values, [3, 5])


def test_vertical_and_horizontal_vertices() -> None:
    """Orientation changes finite rectangle geometry around the baseline."""
    layer = Bar([[2, 5]], baseline=1, width=2)
    np.testing.assert_array_equal(layer._rectangle_vertices()[0], [[1, 1], [3, 1], [3, 5], [1, 5]])

    layer.orientation = "horizontal"
    assert layer.orientation is BarOrientation.HORIZONTAL
    np.testing.assert_array_equal(layer._rectangle_vertices()[0], [[1, 1], [5, 1], [5, 3], [1, 3]])


def test_bar_colors_selection_and_removal() -> None:
    """Per-bar styles survive selection and selected bars can be removed."""
    layer = Bar(
        [[0, 1], [1, 2]],
        fill_color=["red", "blue"],
        border_color=["black", "white"],
    )
    layer.selected_data = {1}
    _, _, vertex_colors = layer._mesh_data()
    np.testing.assert_array_equal(vertex_colors[4], layer._highlight_color)

    layer.remove_selected()
    assert len(layer.data) == 1
    assert layer.fill_color.shape == (1, 4)
    assert layer.border_color.shape == (1, 4)


def test_bar_hit_testing_and_validation() -> None:
    """Bars can be located from canvas coordinates and validate geometry."""
    layer = Bar([[2, 5]], baseline=1, width=2)
    assert layer._get_value((3, 2)) == 0
    assert layer._get_value((8, 2)) is None

    with pytest.raises(ValueError, match="positive"):
        Bar([1], width=0)
    with pytest.raises(ValueError, match="position/value"):
        Bar(np.zeros((2, 3)))


def test_bar_x_region_extent_respects_orientation() -> None:
    """Autoscaling uses only bars intersecting the selected x interval."""
    layer = Bar([[1, 4], [10, 8]], baseline=0, width=2)
    assert layer._get_x_region_extent(0, 3) == (0, 4)
    assert layer._get_x_region_extent(20, 30) == (None, None)

    layer.orientation = "horizontal"
    assert layer._get_x_region_extent(3, 5) == (0, 11)
    assert layer._get_x_region_extent(20, 30) == (None, None)


def test_shift_click_toggles_bar_selection(QtMouseEvent) -> None:
    """Shift-click selects a bar and a second click deselects it."""
    layer = Bar([[2, 5]], baseline=1, width=2)
    event = QtMouseEvent(
        type="mouse_press",
        is_dragging=False,
        modifiers=["Shift"],
        pos=(3, 2),
        position=(3, 2),
    )

    _select_bar(layer, event)
    assert layer.selected_data == {0}
    _select_bar(layer, event)
    assert layer.selected_data == set()
