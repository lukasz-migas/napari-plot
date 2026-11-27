"""Tests for the plot grid overlay."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import numpy as np
import pytest
from napari._vispy.utils.qt_font import FontInfo, QtFontManager

from napari_plot._vispy.overlays.grid_lines import VispyGridLinesOverlay
from napari_plot.components.viewer_model import ViewerModel

if TYPE_CHECKING:
    from collections.abc import Callable

    from napari_plot import Viewer
    from napari_plot._vispy.canvas import VispyCanvas


@pytest.mark.parametrize(("theme", "channel"), [("light", 0), ("dark", 1)])
def test_grid_color_tracks_canvas_background(theme: str, channel: int) -> None:
    """Use the initial background, follow changes, and honor an explicit color."""
    viewer = ViewerModel()
    viewer.theme = theme
    overlay = viewer.grid_lines
    visual = VispyGridLinesOverlay(
        viewer=viewer, overlay=overlay, font_info=FontInfo(face="Arial", font_manager=QtFontManager())
    )
    try:
        assert overlay is viewer.canvas.overlays.grid_lines
        assert not visual.node.visible
        assert visual.node.width == 0.5
        assert visual.node.opacity == pytest.approx(0.25)
        np.testing.assert_allclose(visual.node.color, [channel, channel, channel, 1])

        overlay.visible = True
        assert visual.node.visible
        viewer.theme = "dark" if theme == "light" else "light"
        np.testing.assert_allclose(visual.node.color, [1 - channel] * 3 + [1])

        viewer.canvas.background_color_override = "white" if channel == 0 else "black"
        np.testing.assert_allclose(visual.node.color, [channel, channel, channel, 1])
        overlay.color = (1.0, 0.0, 0.0, 0.5)
        viewer.canvas.background_color_override = None
        viewer.theme = theme
        np.testing.assert_allclose(visual.node.color, [1, 0, 0, 0.5])

        overlay.color = None
        np.testing.assert_allclose(visual.node.color, [channel, channel, channel, 1])
        overlay.opacity = 0.5
        assert visual.node.opacity == pytest.approx(0.5)
        overlay.width = 2.0
        assert visual.node.width == 2.0
    finally:
        visual.close()
    overlay.width = 3.0
    assert visual.node.width == 2.0


def test_grid_width_must_be_positive() -> None:
    """Zero or negative line widths are rejected."""
    viewer = ViewerModel()
    with pytest.raises(ValueError, match="greater than 0"):
        viewer.grid_lines.width = 0


def _assert_grid_matches_ticks(canvas: VispyCanvas, viewer: Viewer) -> tuple[int, int]:
    """Compare the grid segments with the origins of the major marks on each axis."""
    canvas.grid._prepare_draw(canvas.grid)
    node = canvas._overlay_to_visual[viewer.grid_lines][0].node
    assert node._prepare_draw(node) is not False
    bounds = canvas.view.inner_rect
    limits = ((bounds.left, bounds.right), (bounds.bottom, bounds.top))
    segments = node.pos.reshape(-1, 2, 2)
    counts = []
    for dimension, axis_widget in enumerate((canvas.x_axis.node, canvas.y_axis.node)):
        axis = axis_widget.axis
        major_origins = axis._ticks.pos[: 2 * len(axis._text.text) : 2]
        coordinates = axis_widget.node_transform(canvas.view).map(major_origins)[:, dimension]
        low, high = limits[dimension]
        coordinates = coordinates[(coordinates >= low) & (coordinates <= high)]
        counts.append(len(coordinates))
        lines = segments[segments[:, 0, dimension] == segments[:, 1, dimension]]
        np.testing.assert_allclose(lines[:, 0, dimension], coordinates)
        np.testing.assert_allclose(lines[:, :, 1 - dimension], np.tile(limits[1 - dimension], (len(lines), 1)))
    assert canvas.view in node._clippers
    return counts[0], counts[1]


def test_grid_color_follows_canvas_menu(make_napari_plot_viewer: Callable[[], Viewer]) -> None:
    """The light and dark canvas actions update the visible grid color."""
    viewer = make_napari_plot_viewer()
    viewer.grid_lines.visible = True
    canvas = viewer.window._qt_viewer.canvas
    node = canvas._overlay_to_visual[viewer.grid_lines][0].node
    actions = {action.text(): action for action in viewer.window.view_menu.actions()}

    actions["Use Light canvas"].trigger()
    np.testing.assert_allclose(node.color, [0, 0, 0, 1])
    actions["Use Dark canvas"].trigger()
    np.testing.assert_allclose(node.color, [1, 1, 1, 1])


def test_grid_color_follows_direct_canvas_changes(make_napari_plot_viewer: Callable[[], Viewer]) -> None:
    """Embedded viewers can apply their theme directly to the canvas."""
    viewer = make_napari_plot_viewer()
    viewer.grid_lines.visible = True
    canvas = viewer.window._qt_viewer.canvas
    node = canvas._overlay_to_visual[viewer.grid_lines][0].node

    viewer.theme = "dark"
    canvas.bgcolor = "white"
    np.testing.assert_allclose(node.color, [0, 0, 0, 1])

    viewer.grid_lines.color = "red"
    canvas.bgcolor = "black"
    np.testing.assert_allclose(node.color, [1, 0, 0, 1])
    viewer.grid_lines.color = None
    np.testing.assert_allclose(node.color, [1, 1, 1, 1])


@pytest.mark.parametrize("scale", ["linear", "log", "categorical"])
def test_grid_follows_major_ticks(make_napari_plot_viewer: Callable[[], Viewer], scale: str) -> None:
    """Follow both axis layouts through zoom, pan, and resize."""
    viewer = make_napari_plot_viewer()
    canvas = viewer.window._qt_viewer.canvas
    canvas._scene_canvas.central_widget.size = (900, 650)
    canvas.grid._prepare_draw(canvas.grid)
    if scale == "categorical":
        viewer.axis.x_categories = viewer.axis.y_categories = tuple(map(str, range(10)))
    else:
        viewer.axis.x_scale = viewer.axis.y_scale = scale

    viewer.grid_lines.visible = True
    node = canvas._overlay_to_visual[viewer.grid_lines][0].node
    previous_positions = None
    for rect in ((0.25, 9.75, 0.25, 9.75), (1.5, 8.5, 1.5, 8.5), (0.5, 7.5, 2.5, 9.5)):
        viewer.camera.rect = rect
        assert all(_assert_grid_matches_ticks(canvas, viewer))
        assert node.pos is not previous_positions
        previous_positions = node.pos

    positions = node.pos
    with patch.object(type(canvas.x_axis.node), "node_transform", autospec=True) as node_transform:
        assert node._prepare_draw(node) is not False
        node_transform.assert_not_called()
    assert node.pos is positions

    canvas._scene_canvas.central_widget.size = (700, 400)
    assert all(_assert_grid_matches_ticks(canvas, viewer))
    assert node.pos is not positions


def test_grid_handles_view_without_categories(make_napari_plot_viewer: Callable[[], Viewer]) -> None:
    """Omit grid lines for an axis when every category is outside the view."""
    viewer = make_napari_plot_viewer()
    canvas = viewer.window._qt_viewer.canvas
    canvas._scene_canvas.central_widget.size = (900, 650)
    canvas.grid._prepare_draw(canvas.grid)
    viewer.grid_lines.visible = True
    viewer.axis.x_categories = ("outside",)
    viewer.camera.rect = (0.5, 8.5, 0.5, 8.5)
    x_count, y_count = _assert_grid_matches_ticks(canvas, viewer)
    assert x_count == 0
    assert y_count > 0

    viewer.axis.y_categories = ("outside",)
    node = canvas._overlay_to_visual[viewer.grid_lines][0].node
    assert node._prepare_draw(node) is False


def test_minor_grid_can_be_shown_without_minor_tick_marks(make_napari_plot_viewer: Callable[[], Viewer]) -> None:
    viewer = make_napari_plot_viewer()
    canvas = viewer.window._qt_viewer.canvas
    canvas._scene_canvas.central_widget.size = (900, 650)
    canvas.grid._prepare_draw(canvas.grid)
    viewer.camera.rect = (0, 10, 0, 10)
    viewer.grid_lines.visible = True
    node = canvas._overlay_to_visual[viewer.grid_lines][0].node
    node._prepare_draw(node)
    major_count = len(node.pos)

    viewer.axis.x_minor_ticks = viewer.axis.y_minor_ticks = False
    viewer.grid_lines.minor = True
    node._prepare_draw(node)
    assert len(node.pos) > major_count
    for widget in (canvas.x_axis.node, canvas.y_axis.node):
        visual = widget.axis
        assert len(visual.ticker.minor_tick_origins)
        assert len(visual._ticks.pos) == 2 * len(visual.ticker.major_tick_origins)
