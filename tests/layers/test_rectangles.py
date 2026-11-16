"""Model and public API tests for Rectangles."""

from copy import copy

import numpy as np
import pytest

from napari_plot.components.viewer_model import ViewerModel
from napari_plot.layers import Rectangles


def test_rectangles_geometry_and_extent() -> None:
    viewer = ViewerModel()
    layer = viewer.add_rectangles(centers=[[10, 200], [30, 400]], height=[8, 12], width=4)

    assert isinstance(layer, Rectangles)
    assert viewer.layers[0] is layer
    np.testing.assert_array_equal(layer.data, [[10, 200, 8, 4], [30, 400, 12, 4]])
    np.testing.assert_array_equal(layer.centers, [[10, 200], [30, 400]])
    np.testing.assert_array_equal(layer.extent.data, [[196, 8], [406, 32]])
    layer.show_rectangles = False
    np.testing.assert_array_equal(layer.extent.data, [[196, 8], [406, 32]])
    layer.visible = False
    layer.set_data([[50, 9]], 2, 6)
    np.testing.assert_array_equal(layer.extent.data, [[8, 47], [10, 53]])


@pytest.mark.parametrize(
    ("centers", "height", "width"),
    [
        ([[0, 1, 2]], 1, 1),
        ([[0, np.inf]], 1, 1),
        ([[0, 1]], 0, 1),
        ([[0, 1]], 1, None),
        ([[0, 1]], [1, 2], 1),
        ([[0, 1]], 1, [np.nan]),
    ],
)
def test_rectangles_invalid_update_is_atomic(centers, height, width) -> None:
    layer = Rectangles([[2, 4]], 8, 16, text=["preserved"])
    original = layer.data

    with pytest.raises(ValueError):
        layer.set_data(centers, height, width)

    assert layer.data is original
    np.testing.assert_array_equal(layer.text, ["preserved"])


def test_rectangles_empty_and_resized_styles() -> None:
    layer = Rectangles(
        [[10, 20], [30, 40]],
        2,
        5,
        outline_color=["red", "green"],
        marker_color="blue",
        marker_size=[4, 8],
        marker_symbol=["o", "diamond"],
        text=["{literal}", "two"],
    )
    layer.data = [[10, 21, 1, 5]]
    duplicate = copy(layer)
    duplicate.set_data([[10, 21], [30, 41]], 1, 5)

    np.testing.assert_array_equal(duplicate.outline_color, [[1, 0, 0, 1], [1, 1, 1, 1]])
    np.testing.assert_array_equal(duplicate.marker_color, [0, 0, 1, 1])
    np.testing.assert_array_equal(duplicate.marker_size, [4, 6])
    np.testing.assert_array_equal(duplicate.marker_symbol, ["disc", "disc"])
    np.testing.assert_array_equal(duplicate.text, ["{literal}", ""])
    assert len(layer.data) == 1

    duplicate.data = None
    assert duplicate.data.shape == (0, 4)
    assert np.isnan(duplicate.extent.data).all()
    assert copy(duplicate).data.shape == (0, 4)
    duplicate.set_data([[30, 55]], 2, 7)
    np.testing.assert_array_equal(duplicate.marker_size, [6])
    np.testing.assert_array_equal(duplicate.text, [""])


def test_rectangles_rejects_invalid_style() -> None:
    layer = Rectangles([[10, 20]], 2, 5)
    with pytest.raises(ValueError, match="outline_width"):
        layer.outline_width = np.inf
    with pytest.raises(ValueError, match="marker_size"):
        layer.marker_size = [1, 2]
    with pytest.raises(ValueError, match="Unknown marker symbol"):
        layer.marker_symbol = ["invalid"]
    with pytest.raises(ValueError, match="text must contain"):
        layer.text = ["one", "two"]
    assert layer.outline_width == 1
    assert layer.marker_size == 6
    assert layer.marker_symbol == "disc"
    assert layer.text is None
