"""Hover helpers."""

import numpy as np
import pytest

from napari_plot.utils.hover import (
    HoverInfo,
    PixelMapper,
    elide_middle,
    format_coordinates,
    nearest_index,
    snap_index,
)


def test_nearest_index_handles_ascending_descending_and_outside_values() -> None:
    x = np.array([1.0, 2.0, 3.0, 4.0])

    assert nearest_index(x, 2.4) == 1
    assert nearest_index(x, 2.6) == 2
    assert nearest_index(x, 0.6) == 0
    assert nearest_index(x, 0.4) is None
    assert nearest_index(x, 4.4) == 3
    assert nearest_index(x, 4.6) is None
    assert nearest_index(x[::-1], 2.4) == 2
    assert nearest_index(x[::-1], 3.9) == 0
    assert nearest_index(np.array([]), 1.0) is None
    assert nearest_index(np.array([5.0]), 100.0) == 0


def test_snap_index_picks_highest_point_in_window() -> None:
    x = np.arange(10.0)
    y = np.array([0, 1, 5, 2, 0, 0, 3, 9, 1, 0], dtype=float)

    assert snap_index(x, y, 4.0, 4.0, 4.0) == 4
    assert snap_index(x, y, 4.0, 2.0, 6.0) == 2
    assert snap_index(x, y, 5.0, 3.0, 7.0) == 7
    assert snap_index(x[::-1], y[::-1], 5.0, 3.0, 7.0) == 2  # index of x == 7 in the reversed arrays
    assert snap_index(x, y, 20.0, 18.0, 22.0) is None


def test_elide_middle_keeps_head_and_tail() -> None:
    assert elide_middle("short") == "short"
    assert elide_middle("abcdefghij", 7) == "ab...ij"
    text = "Seg PCA.ppm=5.0_centroids_n_peaks=131;raw;cluster=12"
    elided = elide_middle(text, 40)
    assert len(elided) == 40
    assert elided.startswith("Seg PCA.ppm=5.0")
    assert elided.endswith("cluster=12")


def test_hover_info_format() -> None:
    assert HoverInfo(1234.5, 0.5, 3, "A", "Time", "Counts").format() == "Time: 1,234.5\nCounts: 0.5"
    assert HoverInfo(3.0, 10.0, 3, "A", "", "", (("B", 2.0),)).format() == "x: 3\nA: 10\nB: 2"
    assert format_coordinates(1.5, -2.0) == "x=1.5, y=-2"


def test_pixel_mapper_windows_follow_axis_scale() -> None:
    linear = PixelMapper((0.0, 100.0, 0.0, 10.0), (200.0, 100.0))
    assert linear.x_window(50.0, 2.0) == pytest.approx((49.0, 51.0))
    assert linear.y_window(5.0, 10.0) == pytest.approx((4.0, 6.0))
    px, py = linear.to_pixels([0.0, 100.0], [0.0, 10.0])
    assert np.diff(px)[0] == pytest.approx(200.0)
    assert np.diff(py)[0] == pytest.approx(100.0)

    # 3 decades over 300 pixels: 2 pixels around 100 span 10 ** +-0.02
    log = PixelMapper((1.0, 1000.0, 0.0, 10.0), (300.0, 100.0), x_scale="log")
    assert log.x_window(100.0, 2.0) == pytest.approx((100 * 10**-0.02, 100 * 10**0.02))
    # non-positive values have no place on a log axis
    assert log.x_window(-1.0, 2.0) == (-1.0, -1.0)
    assert not np.isfinite(log.to_pixels(-1.0, 1.0)[0])
