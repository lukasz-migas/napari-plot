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


def _assert_axes_match_cameras(canvas: VispyCanvas) -> None:
    """Every axis shows the range of its cell's camera."""
    for cell in canvas._cells:
        rect = cell.view.camera.rect
        assert cell.x_axis.node.axis.domain == pytest.approx((rect.left, rect.right), abs=1e-6)
        assert cell.y_axis.node.axis.domain == pytest.approx((rect.bottom, rect.top), abs=1e-6)


def test_axes_follow_cells_moved_by_grid_layout(plot, qtbot) -> None:
    """Axes refresh their ticks when the grid moves them without a resize or camera change."""
    viewer, canvas = plot
    viewer.camera.rect = (2, 6, -0.5, 1.5)
    _settle(qtbot, canvas)
    _assert_axes_match_cameras(canvas)

    viewer.canvas.grid.enabled = True
    _settle(qtbot, canvas)
    _assert_axes_match_cameras(canvas)

    viewer.canvas.grid.enabled = False
    _settle(qtbot, canvas)
    _assert_axes_match_cameras(canvas)


def test_canvas_corners_span_one_cell_in_grid_mode(plot, qtbot) -> None:
    """Layers decide their level of detail from the range of one cell, since all cells show the same range."""
    viewer, canvas = plot
    viewer.camera.rect = (2.0, 6.0, -0.5, 1.5)
    viewer.canvas.grid.enabled = True
    _settle(qtbot, canvas)
    canvas._set_active_cell(canvas._cells[2])
    corners = canvas._canvas_corners_in_world
    assert corners == pytest.approx(np.array([[1.5, 2.0], [-0.5, 6.0]]), abs=1e-6)
    assert canvas._draw_shape_threshold == pytest.approx(canvas.view.size)


def test_resize_rebuilds_grid_only_when_spacing_changes(plot, qtbot, monkeypatch: pytest.MonkeyPatch) -> None:
    """A canvas resize re-lays out the cells only when it changes the spacing between them."""
    viewer, canvas = plot
    viewer.canvas.grid.spacing = 10
    viewer.canvas.grid.enabled = True
    calls = []
    monkeypatch.setattr(canvas, "_update_scenegraph", lambda *_args: calls.append(1))
    resize = SimpleNamespace(size=canvas._scene_canvas.size)
    canvas.on_resize(resize)
    assert not calls

    monkeypatch.setattr(type(viewer.canvas.grid), "_compute_canvas_spacing", lambda *_args: 4)
    canvas.on_resize(resize)
    assert calls == [1]


@pytest.mark.parametrize("scale", [1, 2])
def test_screenshot_draws_each_layer_in_its_cell(plot, qtbot, scale: int) -> None:
    """Scaled canvas screenshots re-lay out the grid and draw every layer in its own cell."""
    viewer, canvas = plot
    # let the screenshot resize the canvas
    canvas.native.setMinimumSize(200, 200)
    canvas.native.setMaximumSize(16777215, 16777215)
    colors = ([255, 0, 0], [0, 255, 0], [0, 0, 255])
    for layer, color in zip(viewer.layers, colors, strict=True):
        layer.color = np.asarray(color) / 255
        layer.width = 5
    viewer.canvas.grid.enabled = True
    viewer.reset_view()
    _settle(qtbot, canvas)
    size = canvas.size
    offsets = [canvas._view_offset(cell.view) for cell in canvas._cells]
    view_size = np.asarray(canvas.view.size)

    image = viewer.window.screenshot(flash=False, canvas_only=True, scale=scale)
    ratio = image.shape[0] / size[0]  # canvas size is (height, width)
    assert ratio == pytest.approx(scale * canvas.native.devicePixelRatio(), rel=0.02)
    for offset, color in zip(offsets, colors, strict=True):
        left, top = (offset * ratio).astype(int)
        width, height = (view_size * ratio).astype(int)
        cell = image[top : top + height, left : left + width, :3].astype(int)
        assert (np.abs(cell - color).sum(axis=-1) < 60).sum() > 20
    assert canvas.size == size
    assert len(canvas._cells) == 3


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


def test_toolbar_labels_follow_their_layers_between_plot_cells(
    make_napari_plot_viewer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The toolbar shows live layer names and keeps labels in the cell containing their plot."""
    monkeypatch.setattr("napari_plot._vispy.canvas.get_max_texture_sizes", lambda: (2048, 2048))
    monkeypatch.setattr("napari._vispy.layers.base.get_max_texture_sizes", lambda: (2048, 2048))
    viewer = make_napari_plot_viewer(show=False)
    canvas = viewer.window._qt_viewer.canvas
    viewer.add_line([[0, 0], [10, 1]], name="first")
    viewer.add_line([[0, 1], [10, 2]], name="second")
    toolbar = viewer.window._qt_viewer.viewerToolbar
    controls = toolbar.display_controls
    assert not controls.layer_labels_btn.isChecked()

    viewer.grid_lines.visible = False
    controls.grid_btn.click()
    controls.layer_labels_btn.click()
    assert viewer.canvas.grid.enabled
    assert not viewer.grid_lines.visible
    assert all(layer.name_overlay.visible for layer in viewer.layers)
    canvas._update_overlay_canvas_positions()
    for layer, cell in zip(viewer.layers, canvas._cells, strict=True):
        visual = canvas._layer_name_visuals[layer]
        assert visual.node.parent is cell.view
        assert visual.node.visible
        assert visual.node.text == layer.name
        assert visual.node.transform.translate[:2] == pytest.approx(viewer.canvas.overlay_tiling.padding)

    layer = viewer.layers[1]
    visual = canvas._layer_name_visuals[layer]
    layer.name = "renamed"
    assert visual.node.text == "renamed"
    layer.visible = False
    assert not visual.node.visible

    viewer.canvas.grid.enabled = False
    assert not controls.grid_btn.isChecked()
    assert visual.node.parent is canvas.view
    viewer.layers.remove(layer)
    assert visual.node.parent is None

    controls.colorbar_btn.click()
    assert viewer.colorbar.visible
    assert canvas.colorbar.node.visible
    viewer.colorbar.visible = False
    assert not controls.colorbar_btn.isChecked()


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


def test_gridded_legend_lists_only_the_layers_of_its_cell(plot, qtbot) -> None:
    """Each cell's legend shows its own layers; manual and unassigned rows stay visible."""
    viewer, canvas = plot
    viewer.legend.visible = True
    viewer.legend.gridded = True
    viewer.canvas.grid.enabled = True

    def labels() -> list[list[str]]:
        return [[entry.label for entry in visual._entries] for visual in canvas._overlay_to_visual[viewer.legend]]

    assert labels() == [["line 0"], ["line 1"], ["line 2"]]
    visuals = canvas._overlay_to_visual[viewer.legend]
    assert visuals[1].x_size < visuals[1].y_size * 10
    assert visuals[1].y_size < canvas._overlay_to_visual[viewer.legend][0].y_size * 1.5

    viewer.layers[2].name = "renamed"
    assert labels() == [["line 0"], ["line 1"], ["renamed"]]

    # rows without a layer, or for a layer not shown in any cell, are listed in the first cell
    viewer.set_legend([{"label": "note"}, {"label": "gone", "layer_name": "missing"}, *viewer.legend.entries])
    viewer.legend.gridded = True
    assert labels() == [["note", "gone", "line 0"], ["note", "line 1"], ["note", "renamed"]]

    viewer.legend.gridded = False
    assert labels() == [["note", "gone", "line 0", "line 1", "renamed"]]


def test_gridded_legend_click_toggles_the_layer_of_its_cell(plot, qtbot) -> None:
    """Clicking a row of a cell's legend toggles the layer listed in that cell."""
    viewer, canvas = plot
    viewer.legend.visible = True
    viewer.legend.gridded = True
    viewer.canvas.grid.enabled = True
    visual = canvas._overlay_to_visual[viewer.legend][2]
    _settle(qtbot, canvas)
    canvas._update_overlay_canvas_positions()

    origin = visual.node.node_transform(canvas._scene_canvas.central_widget).map([0, 0])[:2]
    event = SimpleNamespace(pos=(origin[0] + 5, origin[1] + viewer.legend.padding + 2), button=1, handled=False)
    visual._on_mouse_press(event)
    assert event.handled
    assert [layer.visible for layer in viewer.layers] == [True, True, False]


def _double_click(canvas: VispyCanvas, pos: np.ndarray, button: int = 1) -> None:
    """Send a double-click through the scene canvas, like vispy does for a real click."""
    canvas._scene_canvas.events.mouse_double_click(pos=tuple(pos), button=button, modifiers=())


def _widget_center(canvas: VispyCanvas, widget) -> np.ndarray:
    origin = widget.node_transform(canvas._scene_canvas.central_widget).map([0, 0])[:2]
    return origin + np.asarray(widget.size) / 2


@pytest.mark.parametrize("grid", [False, True])
def test_double_click_on_an_axis_resets_its_range(plot, qtbot, grid: bool) -> None:
    """Double-clicking the x- or y-axis of any cell resets that range; the plot area and other buttons do nothing."""
    viewer, canvas = plot
    viewer.canvas.grid.enabled = grid
    _settle(qtbot, canvas)
    xmin, xmax, ymin, ymax = viewer._get_rect_extent()
    zoomed = (2.0, 6.0, 1.0, 1.5)
    assert len(canvas._cells) == (3 if grid else 1)

    for cell in canvas._cells:
        viewer.camera.rect = zoomed
        _double_click(canvas, _widget_center(canvas, cell.x_axis.node))
        assert viewer.camera.rect == pytest.approx((xmin, xmax, 1.0, 1.5), abs=1e-5)

        viewer.camera.rect = zoomed
        _double_click(canvas, _widget_center(canvas, cell.y_axis.node))
        assert viewer.camera.rect == pytest.approx((2.0, 6.0, ymin, ymax), abs=1e-5)

        viewer.camera.rect = zoomed
        _double_click(canvas, _widget_center(canvas, cell.view))
        _double_click(canvas, _widget_center(canvas, cell.x_axis.node), button=2)
        assert viewer.camera.rect == pytest.approx(zoomed)
