"""Tests for the canvas grid mode: one plot cell per layer group with synchronized cameras."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import numpy as np
import pytest

if TYPE_CHECKING:
    from napari_plot import Viewer
    from napari_plot._vispy.canvas import VispyCanvas


@pytest.fixture
def plot(make_napari_plot_viewer, qtbot, monkeypatch: pytest.MonkeyPatch) -> tuple[Viewer, VispyCanvas]:
    """Shown viewer with three lines and a fixed-size canvas."""
    monkeypatch.setattr("napari_plot._vispy.canvas.get_max_texture_sizes", lambda: (2048, 2048))
    viewer = make_napari_plot_viewer(show=True)
    canvas = viewer.window._qt_viewer.canvas
    canvas.native.setFixedSize(800, 600)
    for i in range(3):
        viewer.add_line([[0, i], [10, i + 1]], name=f"line {i}")
    qtbot.waitUntil(lambda: canvas.view.size[0] > 300)
    return viewer, canvas


def _settle(qtbot, canvas: VispyCanvas) -> None:
    """Draw the canvas so the grid layout is solved."""
    canvas._scene_canvas.update()
    qtbot.wait(50)
    canvas.grid._prepare_draw(canvas.grid)


def test_grid_puts_each_layer_in_its_own_cell(plot, qtbot) -> None:
    """Each visible layer gets a plot cell with its own view and axes; disabling restores the single plot."""
    viewer, canvas = plot
    viewer.canvas.grid.enabled = True
    assert len(canvas._cells) == 3
    assert canvas._cells[0].view is canvas.view
    assert len({id(cell.view) for cell in canvas._cells}) == 3
    assert len({id(cell.x_axis) for cell in canvas._cells}) == 3
    for cell, layer in zip(canvas._cells, viewer.layers, strict=True):
        assert canvas.layer_to_visual[layer].node.parent is cell.data_scene

    _settle(qtbot, canvas)
    widths = [cell.view.size[0] for cell in canvas._cells]
    assert all(width > 50 for width in widths)
    assert max(widths) < canvas.grid.size[0] / 2

    viewer.canvas.grid.stride = 3
    assert len(canvas._cells) == 1

    viewer.canvas.grid.stride = 1
    viewer.layers[1].visible = False
    assert len(canvas._cells) == 2

    viewer.canvas.grid.enabled = False
    assert len(canvas._cells) == 1
    assert canvas._cells_grid is None
    assert canvas.view.parent is canvas.grid
    assert canvas.x_axis.node.parent is canvas.grid
    for layer in viewer.layers:
        assert canvas.layer_to_visual[layer].node.parent is canvas._data_scene


def test_grid_cameras_stay_synchronized(plot, qtbot) -> None:
    """Enabling the grid keeps the current zoom and zooming any cell updates the model and the other cells."""
    viewer, canvas = plot
    viewer.camera.rect = (2.0, 6.0, 0.5, 2.5)
    viewer.canvas.grid.enabled = True
    for cell in canvas._cells:
        assert cell.camera.rect == pytest.approx((2.0, 6.0, 0.5, 2.5))

    canvas._cells[2].camera.rect = (1.0, 4.0, 0.0, 2.0)
    assert viewer.camera.rect == pytest.approx((1.0, 4.0, 0.0, 2.0))
    _settle(qtbot, canvas)
    for cell in canvas._cells:
        assert cell.camera.rect == pytest.approx((1.0, 4.0, 0.0, 2.0))
    assert viewer.camera.rect == pytest.approx((1.0, 4.0, 0.0, 2.0))


def test_grid_mouse_maps_through_the_cell_under_cursor(plot, qtbot) -> None:
    """Canvas positions map to world coordinates through the cell they fall in."""
    viewer, canvas = plot
    viewer.camera.rect = (0.0, 10.0, 0.0, 4.0)
    viewer.canvas.grid.enabled = True
    _settle(qtbot, canvas)
    for cell in canvas._cells:
        center = canvas._view_offset(cell.view) + np.asarray(cell.view.size) / 2
        assert canvas._cell_at(center) is cell
        y, x = canvas._map_canvas2world(center)
        assert x == pytest.approx(5.0, abs=0.1)
        assert y == pytest.approx(2.0, abs=0.1)

    canvas._set_active_cell(canvas._cells[1])
    assert canvas.tool._polygon.node.parent is canvas._cells[1].data_scene


def test_gridded_overlays_are_copied_per_cell(plot, qtbot) -> None:
    """Gridded overlays get a visual in every cell and are tiled in each; others stay in the first cell."""
    viewer, canvas = plot
    viewer.grid_lines.visible = True
    text = viewer.text_overlay
    text.text = "title"
    text.position = "top_left"
    text.visible = True
    viewer.canvas.grid.enabled = True

    grid_visuals = canvas._overlay_to_visual[viewer.grid_lines]
    assert [visual.node.parent for visual in grid_visuals] == [cell.view for cell in canvas._cells]
    assert len(canvas._overlay_to_visual[text]) == 1

    text.gridded = True
    text_visuals = canvas._overlay_to_visual[text]
    assert [visual.node.parent for visual in text_visuals] == [cell.view for cell in canvas._cells]
    qtbot.waitUntil(lambda: all(visual.x_size > 0 for visual in text_visuals))
    canvas._update_overlay_canvas_positions()
    x_padding, y_padding = viewer.canvas.overlay_tiling.padding
    for visual in text_visuals:
        assert visual.node.transform.translate[:2] == pytest.approx([x_padding, y_padding])

    viewer.canvas.grid.enabled = False
    assert len(canvas._overlay_to_visual[text]) == 1
    assert len(canvas._overlay_to_visual[viewer.grid_lines]) == 1
    assert canvas._overlay_to_visual[text][0].node.parent is canvas.view


def test_legend_click_in_grid_cell(plot, qtbot) -> None:
    """Legend rows stay clickable when the legend's view is nested in a plot cell."""
    viewer, canvas = plot
    viewer.legend.visible = True
    viewer.canvas.grid.enabled = True
    visual = canvas._overlay_to_visual[viewer.legend][0]
    qtbot.waitUntil(lambda: visual.x_size > 0)
    _settle(qtbot, canvas)
    canvas._update_overlay_canvas_positions()

    origin = visual.node.node_transform(canvas._scene_canvas.central_widget).map([0, 0])[:2]
    first_row = viewer.legend.padding + 2
    event = SimpleNamespace(pos=(origin[0] + 5, origin[1] + first_row), button=1, handled=False)
    label = viewer.legend.entries[0].layer_name
    visual._on_mouse_press(event)
    assert event.handled
    assert not viewer.layers[label].visible
