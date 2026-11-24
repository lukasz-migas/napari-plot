"""Data values and hover points reported by plot layers."""

import numpy as np

from napari_plot.layers import Centroids, InfLine, Line, MultiLine, Scatter
from napari_plot.utils.hover import HoverPoint, PixelMapper

# 10 data units over 100 pixels on both axes
MAPPER = PixelMapper((0.0, 10.0, 0.0, 10.0), (100.0, 100.0))


def test_line_value_and_hover_point() -> None:
    layer = Line(np.c_[np.arange(10.0), np.arange(10.0) ** 2], name="square")
    assert layer._get_value((0.0, 3.2)) == 9.0
    assert layer._get_value((0.0, 20.0)) is None
    # within two pixels the highest point wins
    assert layer._get_hover_point(3.1, 5.0, MAPPER) == HoverPoint(3.0, 9.0, 3, "square")
    assert layer._get_hover_point(30.0, 5.0, MAPPER) is None
    assert Line(np.empty((0, 2)))._get_hover_point(3.0, 5.0, MAPPER) is None


def test_multiline_value_and_hover_point_pick_closest_line() -> None:
    layer = MultiLine({"xs": [np.arange(10.0)], "ys": [np.arange(10.0), 2 * np.arange(10.0)]}, name="lines")
    assert layer._get_value((7.0, 3.0)) == (1, 6.0)
    assert layer._get_value((2.0, 3.0)) == (0, 3.0)
    assert layer._get_hover_point(3.0, 7.0, MAPPER) == HoverPoint(3.0, 6.0, 3, "lines [1]")
    assert layer._get_hover_point(3.0, 2.0, MAPPER) == HoverPoint(3.0, 3.0, 3, "lines [0]")


def test_centroids_value_and_hover_point() -> None:
    data = np.array([[1.0, 5.0], [3.0, 8.0], [3.1, 2.0]])
    layer = Centroids(data, name="peaks")
    assert layer._get_value((0.0, 3.08)) == 2.0  # status positions are (y, x)
    # within two pixels (0.2 units) the tallest centroid wins
    assert layer._get_hover_point(3.08, 1.0, MAPPER) == HoverPoint(3.0, 8.0, 1, "peaks")
    assert layer._get_hover_point(6.0, 1.0, MAPPER) is None

    layer.orientation = "horizontal"  # positions are along y
    assert layer._get_value((3.08, 0.0)) == 2.0
    assert layer._get_hover_point(1.0, 3.08, MAPPER) == HoverPoint(8.0, 3.0, 1, "peaks")
    assert layer._get_hover_point(1.0, 6.0, MAPPER) is None


def test_scatter_hover_point_uses_screen_distance() -> None:
    layer = Scatter(np.array([[1.0, 2.0], [5.0, 5.0]]), name="dots")  # stored as (y, x)
    assert layer._get_hover_point(2.5, 1.0, MAPPER) == HoverPoint(2.0, 1.0, 0, "dots")
    assert layer._get_hover_point(3.0, 1.0, MAPPER) is None  # 10 pixels away
    layer.shown = [False, True]
    assert layer._get_hover_point(2.0, 1.0, MAPPER) is None


def test_other_layers_report_no_hover_point() -> None:
    assert InfLine([1.0])._get_hover_point(1.0, 1.0, MAPPER) is None
