"""Tests for the Areas layer."""

import numpy as np
import pytest

from napari_plot.layers import Areas
from napari_plot.layers.band import band_triangles


def test_areas_accepts_list_of_t_lo_hi_arrays() -> None:
    """Areas store one array per region and broadcast colors."""
    layer = Areas([[[0, 0, 1], [1, 0, 2]], [[2, -1, 1], [3, -2, 2], [4, 0, 0]]], fill_color="red")
    assert len(layer.data) == 2
    assert layer.fill_color.shape == (2, 4)
    np.testing.assert_array_equal(layer.fill_color[1], [1, 0, 0, 1])

    vertices, faces, face_colors = layer._mesh_data()
    assert faces.shape == (6, 3)
    assert face_colors.shape == (6, 4)
    assert vertices.shape == (18, 2)


def test_areas_orientation_swaps_coordinates_and_extent() -> None:
    """Horizontal areas run t along y and place lo/hi on x."""
    layer = Areas([[[0, -1, 1], [10, -2, 2]]])
    np.testing.assert_array_equal(layer._extent_data, [[-2, 0], [2, 10]])
    assert layer._get_x_region_extent(5, 6) == (-2, 2)

    layer.orientation = "horizontal"
    np.testing.assert_array_equal(layer._extent_data, [[0, -2], [10, 2]])
    vertices, _, _ = layer._mesh_data()
    assert vertices[:, 1].max() == 10
    assert layer._get_x_region_extent(-0.5, 0.5) == (0, 10)
    assert layer._get_x_region_extent(5, 6) == (None, None)


def test_areas_border_is_closed_outline() -> None:
    """Each outline traces lo forward, hi backward, and closes."""
    layer = Areas([[[0, 0, 1], [1, 0, 1]]], border_color=["blue"])
    segments, colors = layer._border_data()
    assert segments.shape == (8, 2)
    np.testing.assert_array_equal(segments[0], segments[-1])
    np.testing.assert_array_equal(colors[0], [0, 0, 1, 1])


def test_areas_validation_and_resizing() -> None:
    """Invalid shapes are rejected and colors resize with data."""
    with pytest.raises(ValueError, match="t, lo, hi"):
        Areas([[[0, 1, 2]]])
    with pytest.raises(ValueError, match="one color per area"):
        Areas([[[0, 0, 1], [1, 0, 1]]], fill_color=["red", "blue"])
    with pytest.raises(ValueError, match="nonnegative"):
        Areas(border_width=-1)

    layer = Areas()
    assert layer._mesh_data()[1].shape == (0, 3)
    np.testing.assert_array_equal(layer._extent_data, np.full((2, 2), np.nan))
    layer.data = [[[0, 0, 1], [1, 0, 1]]] * 3
    assert layer.fill_color.shape == (3, 4)


def test_band_triangles_split_crossing_bounds() -> None:
    """Crossing bounds meet at the intersection instead of folding."""
    triangles = band_triangles(np.array([[0, 0, 2]]), np.array([[2, 2, 0]]))
    np.testing.assert_allclose(triangles[0, 2], [1, 1])


def test_areas_get_value_returns_area_under_position() -> None:
    """Picking interpolates each area's lo/hi at the cursor and respects orientation."""
    layer = Areas([[[0, 0, 1], [10, 0, 1]], [[0, 2, 3], [10, 4, 5]]])
    assert layer.get_value((0.5, 5)) == 0  # (y, x)
    assert layer.get_value((4.0, 5)) == 1  # second area spans y 3..4 at x=5
    assert layer.get_value((1.5, 5)) is None
    assert layer.get_value((0.5, 11)) is None

    layer.orientation = "horizontal"  # t is y, lo/hi are x
    assert layer.get_value((5, 0.5)) == 0
    assert Areas().get_value((0, 0)) is None


def test_areas_stream_keeps_colors_and_skips_data_events() -> None:
    """Streaming replaces the areas, keeps the colors and emits only the stream event."""
    layer = Areas([[[0, 0, 1], [1, 0, 2]], [[0, 0, 1], [1, 0, 2]]], fill_color=["red", "blue"])
    events = []
    layer.events.data.connect(lambda _event: events.append("data"))
    layer.events.stream.connect(lambda _event: events.append("stream"))
    layer.stream([[[0, 0, 3], [2, 0, 4]], [[0, 0, 5], [2, 0, 6], [3, 0, 1]]])
    assert events == ["stream"]
    assert layer.data[1].shape == (3, 3)
    np.testing.assert_array_equal(layer.fill_color[:, :3], [[1, 0, 0], [0, 0, 1]])

    # a new number of areas reuses the first color
    layer.stream([[[0, 0, 3], [2, 0, 4]]])
    np.testing.assert_array_equal(layer.fill_color, [[1, 0, 0, 1]])


def test_areas_stream_refreshes_the_cached_extent() -> None:
    """The extent read after a stream follows the streamed areas."""
    layer = Areas([[[0, 0, 1], [1, 0, 2]]])
    assert layer.extent.data[1, 0] == 2  # cached
    layer.stream([[[0, 0, 5], [3, 0, 9]]])
    np.testing.assert_array_equal(layer.extent.data, [[0, 0], [9, 3]])
