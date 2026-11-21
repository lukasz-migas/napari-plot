"""Tests for tiling canvas overlays so overlays sharing a position do not overlap."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

from napari_plot._vispy.canvas import _tile_axis

if TYPE_CHECKING:
    from napari.components.overlays import TextOverlay

    from napari_plot import Viewer
    from napari_plot._vispy.canvas import VispyCanvas


@pytest.mark.parametrize(
    ("side", "stacked", "expected"),
    [
        ("left", False, [10.0, 10.0]),
        ("right", False, [70.0, 60.0]),
        ("center", False, [40.0, 35.0]),
        ("top", True, [10.0, 40.0]),
        ("bottom", True, [70.0, 30.0]),
        # group of 20 + 10 + 30 = 60 centered in 100
        ("middle", True, [20.0, 50.0]),
    ],
)
def test_tile_axis(side: str, stacked: bool, expected: list[float]) -> None:
    """Footprints are anchored at the padding, stacked with a padding gap, or centered as a group."""
    assert _tile_axis(side, [20.0, 30.0], 100.0, 10.0, stacked=stacked) == pytest.approx(expected)


@pytest.fixture
def plot(make_napari_plot_viewer, qtbot, monkeypatch: pytest.MonkeyPatch) -> tuple[Viewer, VispyCanvas]:
    """Shown viewer with a line and a fixed-size canvas."""
    monkeypatch.setattr("napari_plot._vispy.canvas.get_max_texture_sizes", lambda: (2048, 2048))
    viewer = make_napari_plot_viewer(show=True)
    canvas = viewer.window._qt_viewer.canvas
    canvas.native.setFixedSize(600, 400)
    viewer.add_line([[0, 0], [1, 1]], name="signal")
    qtbot.waitUntil(lambda: canvas.view.size[0] > 300 and canvas.view.size[1] > 200)
    return viewer, canvas


def _show_text(viewer: Viewer, canvas: VispyCanvas, qtbot, text: str, position: str) -> TextOverlay:
    overlay = viewer.add_text_overlay(text, position=position)
    visual = canvas._overlay_to_visual[overlay][0]
    qtbot.waitUntil(lambda: visual.x_size > 0 and visual.y_size > 0)
    return overlay


def _rect(canvas: VispyCanvas, overlay) -> np.ndarray:
    """Return the (left, top, right, bottom) footprint of an overlay in plot-view pixels."""
    canvas._update_overlay_canvas_positions()
    visual = canvas._overlay_to_visual[overlay][0]
    x, y = np.asarray(visual.node.transform.translate[:2], dtype=float)
    return np.asarray([x, y, x + visual.x_size, y + visual.y_size])


def _disjoint(a: np.ndarray, b: np.ndarray) -> bool:
    return bool(a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def test_same_corner_overlays_stack(plot, qtbot) -> None:
    """Text at the same corner stacks in the order it was added, separated by the tiling padding."""
    viewer, canvas = plot
    first = _show_text(viewer, canvas, qtbot, "first", "top_left")
    second = _show_text(viewer, canvas, qtbot, "second", "top_left")
    x_padding, y_padding = viewer.canvas.overlay_tiling.padding

    a, b = _rect(canvas, first), _rect(canvas, second)
    assert _disjoint(a, b)
    assert a[:2] == pytest.approx([x_padding, y_padding])
    assert b[0] == pytest.approx(x_padding)
    assert b[1] == pytest.approx(a[3] + y_padding)


def test_hidden_overlay_frees_its_slot(plot, qtbot) -> None:
    """Hiding the overlay closest to the corner moves the next one into its place."""
    viewer, canvas = plot
    first = _show_text(viewer, canvas, qtbot, "first", "bottom_right")
    second = _show_text(viewer, canvas, qtbot, "second", "bottom_right")
    assert _disjoint(_rect(canvas, first), _rect(canvas, second))

    first.visible = False
    width, height = canvas.view.size
    x_padding, y_padding = viewer.canvas.overlay_tiling.padding
    assert _rect(canvas, second)[2:] == pytest.approx([width - x_padding, height - y_padding])


def test_legend_and_text_share_corner(plot, qtbot) -> None:
    """The legend and text in the same corner never overlap, whatever the tiling direction."""
    viewer, canvas = plot
    text = viewer.text_overlay
    text.text = "title"
    text.position = "top_right"
    text.visible = True
    viewer.legend.visible = True
    legend_visual = canvas._overlay_to_visual[viewer.legend][0]
    qtbot.waitUntil(lambda: legend_visual.x_size > 0)

    # the default text overlay is first in the overlay order, so it sits in the corner
    a, b = _rect(canvas, text), _rect(canvas, viewer.legend)
    assert _disjoint(a, b)
    assert b[2] < a[0]  # top_right tiles horizontally by default

    viewer.canvas.overlay_tiling.top_right = "vertical"
    a, b = _rect(canvas, text), _rect(canvas, viewer.legend)
    assert _disjoint(a, b)
    assert b[1] > a[3]


def test_grid_lines_do_not_take_a_slot(plot, qtbot) -> None:
    """Grid lines fill the plot and must not push corner overlays away."""
    viewer, canvas = plot
    text = _show_text(viewer, canvas, qtbot, "note", "bottom_right")
    before = _rect(canvas, text)
    viewer.grid_lines.position = "bottom_right"
    viewer.grid_lines.visible = True
    assert _rect(canvas, text) == pytest.approx(before)


def test_middle_center_group_is_centered(plot, qtbot) -> None:
    """Overlays in the middle of the plot are centered as a group instead of overlapping."""
    viewer, canvas = plot
    first = _show_text(viewer, canvas, qtbot, "first", "middle_center")
    second = _show_text(viewer, canvas, qtbot, "second line", "middle_center")
    a, b = _rect(canvas, first), _rect(canvas, second)
    assert _disjoint(a, b)
    width, height = canvas.view.size
    assert (a[1] + b[3]) / 2 == pytest.approx(height / 2, abs=1)
    assert (a[0] + a[2]) / 2 == pytest.approx(width / 2, abs=1)


def test_plot_area_resize_reanchors_overlays(plot, qtbot) -> None:
    """When the plot area shrinks (e.g. wider y-axis), right-anchored overlays follow its edge."""
    viewer, canvas = plot
    text = _show_text(viewer, canvas, qtbot, "note", "bottom_right")
    visual = canvas._overlay_to_visual[text][0]
    x_padding, _ = viewer.canvas.overlay_tiling.padding
    width = canvas.view.size[0]

    viewer.axis.y_max_size += 50
    qtbot.waitUntil(lambda: canvas.view.size[0] < width)
    # no explicit update: the view resize must trigger the tiling on the next draw
    qtbot.waitUntil(
        lambda: visual.node.transform.translate[0] + visual.x_size == pytest.approx(canvas.view.size[0] - x_padding)
    )
