"""Tests for the canvas grid mode: one plot cell per layer group with synchronized cameras."""

from __future__ import annotations

import gc
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import create_autospec

import numpy as np
import pytest
from qtextra.widgets.qt_toolbar_mini import QtMiniToolbar
from qtpy.QtCore import QPoint, Qt
from vispy.scene import ViewBox, Widget

from napari_plot._qt.component_controls.qt_plot_display_controls import QtPlotDisplayControls
from napari_plot._vispy.components.camera import make_rect

if TYPE_CHECKING:
    from napari.layers import Layer

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


def test_cell_axis_overrides_apply_to_ticks_interactions_and_reset(plot, qtbot) -> None:
    viewer, canvas = plot
    grid = viewer.canvas.grid
    grid.sharex = False
    grid.enabled = True
    first, second, *_ = canvas._cells
    settings = grid.cell(*second.position)
    settings.x_label = "Second x"
    settings.x_scale = "log"
    settings.xlim = (100, 1)
    _settle(qtbot, canvas)

    assert second.x_axis.node.axis.axis_label == "Second x"
    assert second.x_axis.node.axis.scale_type == "logarithmic"
    assert second.camera.camera.flip[0]
    assert second.camera.rect[:2] == pytest.approx((1, 100))
    assert first.camera.rect[:2] != pytest.approx((1, 100))
    assert canvas._map_canvas2world(_widget_center(canvas, second.view))[1] == pytest.approx(10, rel=1e-3)

    second.camera.rect = (2, 20, 0, 2)
    assert first.camera.rect[2:] == pytest.approx((0, 2))
    _double_click(canvas, _widget_center(canvas, second.x_axis.node))
    assert second.camera.rect[:2] == pytest.approx((1, 100))

    grid.enabled = False
    assert canvas.x_axis.node.axis.scale_type == "linear"
    assert not canvas.camera.camera.flip[0]


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


def test_spacing_and_resize_keep_cells_and_legends(plot, qtbot, monkeypatch: pytest.MonkeyPatch) -> None:
    """Spacing changes preserve the attached cells and do not redraw or reassign layers."""
    viewer, canvas = plot
    viewer.legend.visible = True
    viewer.canvas.grid.enabled = True
    _settle(qtbot, canvas)
    grid = canvas._cells_grid
    cells = tuple(canvas._cells)
    layouts = tuple(cell.layout for cell in cells)
    parents = [canvas.layer_to_visual[layer].node.parent for layer in viewer.layers]
    width = canvas._cells[0].view.size[0]
    redraws = []
    detachments = []
    for cell in cells:
        cell.view.events.canvas_change.connect(lambda event: detachments.append(event))
    for visual in canvas._overlay_to_visual[viewer.legend]:
        monkeypatch.setattr(visual, "_on_data_change", lambda *_args: redraws.append(1))
    viewer.canvas.grid.spacing = 15
    assert canvas._cells_grid is grid
    assert tuple(canvas._cells) == cells
    assert all(layout.parent is grid for layout in layouts)
    assert [canvas.layer_to_visual[layer].node.parent for layer in viewer.layers] == parents
    assert not redraws
    assert grid.spacing == 15
    _settle(qtbot, canvas)
    assert canvas._cells[0].view.size[0] < width
    viewer.canvas.grid.spacing = 0.1
    canvas.native.setFixedSize(900, 600)
    qtbot.waitUntil(lambda: canvas._scene_canvas.size[0] == 900)
    assert grid.spacing == viewer.canvas.grid._compute_canvas_spacing(canvas._scene_canvas.size, viewer.layers)
    assert not detachments
    assert not redraws
    monkeypatch.setattr(type(viewer.canvas.grid), "_compute_canvas_spacing", lambda *_args: 4)
    canvas.on_resize(SimpleNamespace(size=canvas._scene_canvas.size))
    assert grid.spacing == 4
    assert canvas._cells_grid is grid
    assert not redraws


def test_grid_model_update_batches_relayout(plot, monkeypatch: pytest.MonkeyPatch) -> None:
    """Combined grid model changes do not create intermediate layouts."""
    viewer, canvas = plot
    calls = []
    layout = canvas._layout_cells

    def track(positions):
        calls.append(positions)
        layout(positions)

    monkeypatch.setattr(canvas, "_layout_cells", track)
    viewer.canvas.grid.update({"enabled": True, "shape": (3, 1), "stride": 2})
    assert len(calls) == 1
    assert len(canvas._cells) == 2


def test_regroup_preserves_surviving_layouts_and_restores_from_hidden(plot, qtbot) -> None:
    """Regrouping moves attached layouts, and hiding all layers restores the single view."""
    viewer, canvas = plot
    viewer.canvas.grid.enabled = True
    grid = canvas._cells_grid
    cells = tuple(canvas._cells)
    viewer.canvas.grid.shape = (3, 1)
    assert canvas._cells_grid is grid
    assert tuple(canvas._cells) == cells
    assert all(cell.layout.parent is grid for cell in cells)
    _settle(qtbot, canvas)
    assert all(cell.view.size[0] > 50 for cell in cells)
    for layer in viewer.layers:
        layer.visible = False
    assert canvas._cells_grid is None
    assert canvas.view.parent is canvas.grid
    viewer.layers[0].visible = True
    assert canvas._cells_grid is not None
    assert canvas._cells[0] is cells[0]


def test_cell_resize_only_positions_its_overlays(plot, monkeypatch: pytest.MonkeyPatch) -> None:
    """A cell resize leaves other cells untouched and retains pending global positioning."""
    viewer, canvas = plot
    viewer.text_overlay.text = "title"
    viewer.text_overlay.visible = True
    viewer.text_overlay.gridded = True
    viewer.canvas.grid.enabled = True
    visuals = canvas._overlay_to_visual[viewer.text_overlay]
    calls = []
    for index, visual in enumerate(visuals):
        monkeypatch.setattr(visual, "_on_position_change", lambda *_args, index=index: calls.append(index))
    canvas._needs_overlay_position_update = True
    canvas._update_overlay_canvas_positions(SimpleNamespace(source=canvas._cells[1].view))
    assert calls == [1]
    assert canvas._needs_overlay_position_update


def test_hidden_gridded_overlay_is_lazy_and_reused(plot) -> None:
    """Hidden overlay copies are made on first show and retained on hide."""
    viewer, canvas = plot
    text = viewer.text_overlay
    text.visible = False
    text.gridded = True
    main = canvas._overlay_to_visual[text][0]
    viewer.canvas.grid.enabled = True
    assert canvas._overlay_to_visual[text] == [main]
    text.visible = True
    visuals = tuple(canvas._overlay_to_visual[text])
    assert len(visuals) == len(canvas._cells)
    text.visible = False
    text.visible = True
    assert tuple(canvas._overlay_to_visual[text]) == visuals


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


@pytest.mark.parametrize("mode", ["layer_list", "automatic_legend", "explicit_legend"])
def test_restored_grid_layers_are_drawn(plot, qtbot, mode: str) -> None:
    """Restored layers remain rendered after their former cells are collected."""
    viewer, canvas = plot
    viewer.add_line([[0, 3], [10, 4]], name="line 3")
    colors = ([255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 0])
    for layer, color in zip(viewer.layers, colors, strict=True):
        layer.color = np.asarray(color) / 255
        layer.width = 5
    if mode == "explicit_legend":
        viewer.set_legend([{"label": layer.name, "layer_name": layer.name} for layer in viewer.layers])
    else:
        viewer.set_legend_from_layers()
    viewer.canvas.grid.enabled = True
    viewer.reset_view()
    _settle(qtbot, canvas)

    def set_list_visible(layer: Layer, visible: bool) -> None:
        model = viewer.window._qt_viewer.layers.model().sourceModel()
        index = next(
            model.index(i, 0) for i in range(model.rowCount()) if model.getItemStrict(model.index(i, 0)) is layer
        )
        state = Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked
        assert model.setData(index, state, Qt.ItemDataRole.CheckStateRole)

    def click_legend(layer: Layer) -> None:
        _settle(qtbot, canvas)
        canvas._update_overlay_canvas_positions()
        visual = next(
            visual
            for visual in canvas._overlay_to_visual[viewer.legend]
            if any(entry.layer_name == layer.name for entry in visual._entries)
        )
        row = next(i for i, entry in enumerate(visual._entries) if entry.layer_name == layer.name)
        origin = visual.node.node_transform(canvas._scene_canvas.central_widget).map([0, 0])[:2]
        row_height = max(viewer.legend.effective_font_size, viewer.legend.marker_size) + viewer.legend.row_spacing
        event = SimpleNamespace(
            pos=(origin[0] + 5, origin[1] + viewer.legend.padding + row * row_height + 2),
            button=1,
            handled=False,
        )
        visual._on_mouse_press(event)
        assert event.handled

    for layer in (viewer.layers[2], viewer.layers[3]):
        if mode == "layer_list":
            set_list_visible(layer, False)
        else:
            click_legend(layer)
        assert not layer.visible
        _settle(qtbot, canvas)
        gc.collect()
    for layer in (viewer.layers[2], viewer.layers[3]):
        if mode == "explicit_legend":
            click_legend(layer)
        else:
            set_list_visible(layer, True)
        assert layer.visible
        _settle(qtbot, canvas)
        gc.collect()

    viewer.legend.visible = False
    _settle(qtbot, canvas)
    image = viewer.window.screenshot(flash=False, canvas_only=True)
    ratio = image.shape[0] / canvas.size[0]
    for cell, color in zip(canvas._cells, colors, strict=True):
        left, top = (canvas._view_offset(cell.view) * ratio).astype(int)
        width, height = (np.asarray(cell.view.size) * ratio).astype(int)
        pixels = image[top : top + height, left : left + width, :3].astype(int)
        assert (np.abs(pixels - color).sum(axis=-1) < 60).sum() > 20


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
    label = visual._entries[0].layer_name
    visual._on_mouse_press(event)
    assert event.handled
    assert not viewer.layers[label].visible


def test_gridded_legend_lists_only_the_layers_of_its_cell(plot, qtbot) -> None:
    """Each cell's legend shows its own layers; manual and unassigned rows stay visible."""
    viewer, canvas = plot
    viewer.legend.visible = True
    assert viewer.legend.gridded
    viewer.canvas.grid.enabled = True

    def labels() -> list[list[str]]:
        return [[entry.label for entry in visual._entries] for visual in canvas._overlay_to_visual[viewer.legend]]

    assert labels() == [["line 0"], ["line 1"], ["line 2"]]
    viewer.canvas.grid.stride = 2
    assert labels() == [["line 0", "line 1"], ["line 2"]]
    viewer.canvas.grid.stride = 1
    assert labels() == [["line 0"], ["line 1"], ["line 2"]]
    visuals = canvas._overlay_to_visual[viewer.legend]
    assert visuals[1].x_size < visuals[1].y_size * 10
    assert visuals[1].y_size < canvas._overlay_to_visual[viewer.legend][0].y_size * 1.5

    viewer.layers[2].name = "renamed"
    assert labels() == [["line 0"], ["line 1"], ["renamed"]]

    # rows without a layer, or for a layer not shown in any cell, are listed in the first cell
    viewer.set_legend([{"label": "note"}, {"label": "gone", "layer_name": "missing"}, *viewer.legend.entries])
    assert labels() == [["note", "gone", "line 0"], ["note", "line 1"], ["note", "renamed"]]

    viewer.legend.gridded = False
    assert labels() == [["note", "gone", "line 0", "line 1", "renamed"]]
    viewer.legend.gridded = True
    assert labels() == [["note", "gone", "line 0"], ["note", "line 1"], ["note", "renamed"]]
    viewer.canvas.grid.enabled = False
    assert labels() == [["note", "gone", "line 0", "line 1", "renamed"]]


def test_gridded_legend_redraws_when_entry_layer_changes(plot) -> None:
    """Changing a row's layer redraws both the old and new cell."""
    viewer, canvas = plot
    viewer.set_legend([{"label": "moving row", "layer_name": "line 0"}])
    viewer.canvas.grid.enabled = True
    visuals = canvas._overlay_to_visual[viewer.legend]
    assert visuals[0].y_size > 0
    assert visuals[1].y_size == 0

    viewer.legend.entries[0].layer_name = "line 1"
    assert visuals[0].y_size == 0
    assert visuals[1].y_size > 0
    assert list(visuals[1]._text.text) == ["moving row"]

    viewer.layers[1].name = "renamed"
    assert visuals[0].y_size > 0
    assert list(visuals[0]._text.text) == ["moving row"]
    assert visuals[1].y_size == 0


def test_gridded_legend_click_toggles_the_layer_of_its_cell(plot, qtbot) -> None:
    """Clicking a row of a cell's legend toggles the layer listed in that cell."""
    viewer, canvas = plot
    viewer.legend.visible = True
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


def _drag(canvas: VispyCanvas, start: np.ndarray, *moves: np.ndarray, button: int = 2) -> None:
    """Press at `start`, move through `moves` and release, like vispy does for a real drag."""
    events = canvas._scene_canvas.events
    press = events.mouse_press(pos=tuple(start), button=button, buttons=[button], modifiers=())
    last = press
    for pos in moves:
        last = events.mouse_move(
            pos=tuple(pos), button=button, buttons=[button], modifiers=(), press_event=press, last_event=last
        )
    events.mouse_release(pos=tuple(moves[-1]), button=button, modifiers=(), press_event=press, last_event=last)


@pytest.mark.parametrize("grid", [False, True])
def test_right_drag_on_an_axis_pans_along_it(plot, qtbot, grid: bool) -> None:
    """Right-dragging an axis of any cell moves only that axis range, and does not start the drag tools."""
    viewer, canvas = plot
    viewer.canvas.grid.enabled = grid
    _settle(qtbot, canvas)
    spans = []
    viewer.events.span.connect(spans.append)
    rect = (2.0, 6.0, 0.5, 2.5)

    for cell in canvas._cells:
        width, height = cell.view.size
        viewer.camera.rect = rect
        start = _widget_center(canvas, cell.x_axis.node)
        # dragging right moves the data right, so the range moves left; leaving the axis does not pan y
        _drag(canvas, start, start + (30, 0), start + (50, -height / 2))
        assert viewer.camera.rect == pytest.approx((2.0 - 200 / width, 6.0 - 200 / width, 0.5, 2.5), abs=1e-4)

        viewer.camera.rect = rect
        start = _widget_center(canvas, cell.y_axis.node)
        # dragging down moves the data down, so the range moves up
        _drag(canvas, start, start + (0, 40))
        assert viewer.camera.rect == pytest.approx((2.0, 6.0, 0.5 + 80 / height, 2.5 + 80 / height), abs=1e-4)
        for other in canvas._cells:
            assert other.camera.rect == pytest.approx(viewer.camera.rect, abs=1e-4)
        assert not spans

        # a left-drag on an axis keeps its usual meaning (the drag tool) and does not pan
        viewer.camera.rect = rect
        _drag(canvas, start, start + (0, 40), button=1)
        assert viewer.camera.rect == pytest.approx(rect)
        spans.clear()


@pytest.mark.parametrize("grid", [False, True])
def test_wheel_on_an_axis_zooms_along_it(plot, qtbot, grid: bool) -> None:
    """Scrolling over an axis of any cell zooms only that axis, keeping the value under the mouse in place."""
    viewer, canvas = plot
    viewer.canvas.grid.enabled = grid
    _settle(qtbot, canvas)
    rect = (2.0, 6.0, 0.5, 2.5)

    def wheel(pos: np.ndarray, delta: float, modifiers: tuple = ()) -> None:
        canvas._scene_canvas.events.mouse_wheel(pos=tuple(pos), delta=(0, delta), modifiers=modifiers)

    for cell in canvas._cells:
        offset = canvas._view_offset(cell.view)
        width, height = cell.view.size
        # a quarter along the x-axis and a quarter down the y-axis, so zooming about the mouse is not the center
        x_pos = _widget_center(canvas, cell.x_axis.node) - (width / 4, 0)
        y_pos = _widget_center(canvas, cell.y_axis.node) - (0, height / 4)
        x_value = 2.0 + (x_pos[0] - offset[0]) / width * 4.0
        y_value = 2.5 - (y_pos[1] - offset[1]) / height * 2.0

        for delta, zoom_in in ((1, True), (-1, False)):
            viewer.camera.rect = rect
            wheel(x_pos, delta)
            left, right, bottom, top = viewer.camera.rect
            assert (right - left < 4.0) is zoom_in
            assert (x_value - left) / (right - left) == pytest.approx((x_value - 2.0) / 4.0, abs=1e-4)
            assert (bottom, top) == pytest.approx((0.5, 2.5))

            viewer.camera.rect = rect
            wheel(y_pos, delta)
            left, right, bottom, top = viewer.camera.rect
            assert (top - bottom < 2.0) is zoom_in
            assert (top - y_value) / (top - bottom) == pytest.approx((2.5 - y_value) / 2.0, abs=1e-4)
            assert (left, right) == pytest.approx((2.0, 6.0))
        for other in canvas._cells:
            assert other.camera.rect == pytest.approx(viewer.camera.rect, abs=1e-4)

        # wheel events with modifiers are ignored by the canvas, as in the plot area
        viewer.camera.rect = rect
        wheel(x_pos, 1, modifiers=("Control",))
        assert viewer.camera.rect == pytest.approx(rect)


def test_grid_mouse_events_pick_widgets_without_rendering(plot, qtbot, monkeypatch: pytest.MonkeyPatch) -> None:
    """Wheel and hover find the plot and axes using the layout, without a picking render."""
    viewer, canvas = plot
    grid = viewer.canvas.grid
    grid.sharex = grid.sharey = False
    grid.enabled = True
    _settle(qtbot, canvas)
    scene = canvas._scene_canvas
    cell = canvas._cells[1]
    render_picking = type(scene)._render_picking
    pick = create_autospec(render_picking, side_effect=render_picking)
    monkeypatch.setattr(type(scene), "_render_picking", pick)
    other_rects = [other.camera.rect for other in canvas._cells if other is not cell]

    for widget, changed_axes in (
        (cell.view, (True, True)),
        (cell.x_axis.node, (True, False)),
        (cell.y_axis.node, (False, True)),
    ):
        before = cell.camera.rect
        event = scene.events.mouse_wheel(pos=tuple(_widget_center(canvas, widget)), delta=(0, 1), modifiers=())
        assert event.handled
        after = cell.camera.rect
        for index, changed in zip((0, 2), changed_axes, strict=True):
            if changed:
                assert after[index + 1] - after[index] < before[index + 1] - before[index]
            else:
                assert after[index : index + 2] == pytest.approx(before[index : index + 2])

    assert [other.camera.rect for other in canvas._cells if other is not cell] == other_rects

    hovered = []
    cell.view.events.mouse_move.connect(hovered.append)
    scene.events.mouse_move(pos=tuple(_widget_center(canvas, cell.view)), buttons=[], modifiers=())
    assert len(hovered) == 1
    assert scene.visual_at((1, 1)) is None
    pick.assert_not_called()


def test_grid_mouse_picking_falls_back_for_other_interactive_visuals(
    plot, qtbot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Extra interactive visuals use Vispy picking when their branch is visible."""
    viewer, canvas = plot
    viewer.canvas.grid.enabled = True
    _settle(qtbot, canvas)
    scene = canvas._scene_canvas
    parent = Widget(parent=scene.central_widget, size=(10, 10))
    extra = ViewBox(parent=parent, size=(10, 10))
    extra.interactive = True
    render_picking = type(scene)._render_picking
    pick = create_autospec(render_picking, side_effect=render_picking)
    monkeypatch.setattr(type(scene), "_render_picking", pick)
    parent.visible = False
    assert scene.visual_at((5, 5)) is None
    pick.assert_not_called()

    parent.visible = True
    assert scene.visual_at((5, 5)) is extra
    pick.assert_called_once()


def test_one_axis_zoom_survives_drawing_in_grid_mode(plot, qtbot) -> None:
    """Drawing publishes the camera zoom; the other cells must not apply it back as a uniform zoom of both axes."""
    viewer, canvas = plot
    viewer.canvas.grid.enabled = True
    viewer.camera.rect = (2.0, 6.0, 0.5, 2.5)
    _settle(qtbot, canvas)

    pos = _widget_center(canvas, canvas._cells[0].x_axis.node)
    for delta in (1, 1, -1, -1, -1, -1):
        canvas._scene_canvas.events.mouse_wheel(pos=tuple(pos), delta=(0, delta), modifiers=())
        canvas._scene_canvas.render()
        _settle(qtbot, canvas)
        assert viewer.camera.rect[2:] == pytest.approx((0.5, 2.5), abs=1e-4)

    # the same holds for a box zoom in another cell (values that the cells do not share exactly after rounding)
    for rect in ((3.1234567, 4.7654321, 1.1111111, 2.2222229), (2.2, 7.3, 0.35, 0.91)):
        canvas._cells[1].camera.camera.rect = make_rect(*rect)
        canvas._scene_canvas.render()
        _settle(qtbot, canvas)
        for cell in canvas._cells:
            assert cell.camera.rect == pytest.approx(rect, abs=1e-4)


def test_metadata_grid_updates_canvas_and_menu(make_napari_plot_viewer, monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Metadata reassignment updates visual parents, legend filters, and the toolbar option."""
    monkeypatch.setattr("napari_plot._vispy.canvas.get_max_texture_sizes", lambda: (2048, 2048))
    monkeypatch.setattr("napari._vispy.layers.base.get_max_texture_sizes", lambda: (2048, 2048))
    viewer = make_napari_plot_viewer(show=False)
    canvas = viewer.window._qt_viewer.canvas
    first = viewer.add_line([[0, 0], [1, 1]], name="first", metadata={"napari_plot.group": "a"})
    second = viewer.add_line([[0, 1], [1, 2]], name="second")
    third = viewer.add_line([[0, 2], [1, 3]], name="third", metadata={"napari_plot.group": "a"})
    settings_calls = []
    toolbar = QtMiniToolbar(None)
    qtbot.addWidget(toolbar)
    controls = QtPlotDisplayControls(toolbar, viewer, open_grid_settings=lambda: settings_calls.append(True))
    viewer.set_legend([{"label": layer.name, "layer_name": layer.name} for layer in viewer.layers])
    viewer.legend.visible = True
    viewer.canvas.grid.enabled = True
    controls.grid_btn.customContextMenuRequested.emit(QPoint(0, 0))
    assert controls.grid_menu.isVisible()
    controls.grid_menu.hide()
    controls.grid_menu.actions()[-1].trigger()
    assert settings_calls == [True]
    controls.group_by_metadata_action.trigger()
    assert viewer.canvas.grid.group_by_metadata
    assert canvas._cell_layers == [[first, third], [second]]
    assert [[entry.label for entry in visual._entries] for visual in canvas._overlay_to_visual[viewer.legend]] == [
        ["first", "third"],
        ["second"],
    ]
    assert canvas.layer_to_visual[third].node.parent is canvas._cells[0].data_scene
    second.metadata = {"napari_plot.group": "a"}
    assert canvas._cell_layers == [[first, second, third]]
    assert [entry.label for entry in canvas._overlay_to_visual[viewer.legend][0]._entries] == [
        "first",
        "second",
        "third",
    ]
    assert canvas.layer_to_visual[second].node.parent is canvas._cells[0].data_scene
    second.metadata = {}
    assert canvas._legend_filter(1) == (frozenset({"second"}), True)
    viewer.canvas.grid.group_by_metadata = False
    assert not controls.group_by_metadata_action.isChecked()
    viewer.canvas.grid.update({"group_by_metadata": True})
    assert controls.group_by_metadata_action.isChecked()


def test_joint_grid_layout_and_cameras(plot, qtbot) -> None:
    from napari_plot import JointGrid

    viewer, canvas = plot
    viewer.camera.aspect = 1
    grid = JointGrid(viewer, ratio=4)
    grid.add_layer(viewer.layers[1], panel="top")
    grid.add_layer(viewer.layers[2], panel="right")
    _settle(qtbot, canvas)
    main, top, right = canvas._cells
    assert all(cell.camera.camera.aspect is None for cell in (main, top, right))
    assert [cell.position for cell in canvas._cells] == [(1, 0), (0, 0), (1, 1)]
    assert main.view.size[0] == pytest.approx(top.view.size[0], abs=2)
    assert main.view.size[1] == pytest.approx(right.view.size[1], abs=2)
    assert main.view.size[0] > right.view.size[0] * 2
    assert main.view.size[1] > top.view.size[1] * 2
    viewer.axis.visible = False
    viewer.axis.visible = True
    viewer.axis.x_max_size += 5
    assert not top.x_axis.node.visible
    assert top.x_axis.node.height_max == 0
    canvas.native.setFixedSize(900, 700)
    _settle(qtbot, canvas)
    assert main.view.size[0] == pytest.approx(top.view.size[0], abs=2)
    assert main.view.size[1] == pytest.approx(right.view.size[1], abs=2)
    main.camera.rect = (1, 8, 2, 6)
    assert top.camera.rect[:2] == pytest.approx((1, 8))
    top.camera.rect = (2, 7, 0, 4)
    assert main.camera.rect[:2] == pytest.approx((2, 7))
    right.camera.rect = (0, 3, 4, 9)
    assert main.camera.rect[2:] == pytest.approx((4, 9))
    top_y = top.camera.rect[2:]
    right_x = right.camera.rect[:2]
    before = main.camera.rect
    focus_before = ((4 - before[0]) / (before[1] - before[0]), (6 - before[2]) / (before[3] - before[2]))
    main.camera.camera.zoom((0.5, 0.5), (4, 6))
    after = main.camera.rect
    focus_after = ((4 - after[0]) / (after[1] - after[0]), (6 - after[2]) / (after[3] - after[2]))
    assert focus_after == pytest.approx(focus_before)
    assert top.camera.rect[:2] == pytest.approx(main.camera.rect[:2])
    assert right.camera.rect[2:] == pytest.approx(main.camera.rect[2:])
    assert top.camera.rect[2:] == pytest.approx(top_y)
    assert right.camera.rect[:2] == pytest.approx(right_x)
    top.camera.camera.pan((1, 2))
    right.camera.camera.pan((3, 1))
    top.camera.camera.zoom((0.8, 1), (4, 1))
    right.camera.camera.zoom((1, 0.8), (1, 6))
    assert top.camera.rect[:2] == pytest.approx(main.camera.rect[:2])
    assert right.camera.rect[2:] == pytest.approx(main.camera.rect[2:])
    assert top.camera.rect[2:] != pytest.approx(top_y)
    assert right.camera.rect[:2] != pytest.approx(right_x)
    for a, b, axis in ((main, top, 1), (main, right, 0)):
        point_a = canvas._view_offset(a.view) + np.asarray(a.view.size) * 0.3
        point_b = canvas._view_offset(b.view) + np.asarray(b.view.size) * 0.3
        assert canvas._map_canvas2world(point_a, a.view)[axis] == pytest.approx(
            canvas._map_canvas2world(point_b, b.view)[axis], abs=1e-5
        )
    viewer.axis.y_inverted = True
    viewer.axis.x_inverted = True
    assert not top.camera.camera.flip[1]
    assert not right.camera.camera.flip[0]
    assert top.camera.axis_scale("y") == "linear"
    assert right.camera.axis_scale("x") == "linear"
    viewer.reset_view()
    assert main.camera.rect[:2] == pytest.approx(top.camera.rect[:2])
    assert main.camera.rect[2:] == pytest.approx(right.camera.rect[2:])
    viewer.canvas.grid.enabled = False
    assert canvas.camera.camera.aspect == 1


@pytest.mark.parametrize("panel", ["top", "right"])
def test_joint_grid_single_marginal(plot, qtbot, panel: str) -> None:
    from napari_plot import JointGrid

    viewer, canvas = plot
    grid = JointGrid(viewer, top=panel == "top", right=panel == "right")
    grid.add_layer(viewer.layers[1], panel=panel)
    _settle(qtbot, canvas)
    main, marginal = canvas._cells
    if panel == "top":
        assert [cell.position for cell in canvas._cells] == [(1, 0), (0, 0)]
        assert main.view.size[0] == pytest.approx(marginal.view.size[0], abs=2)
        assert main.view.size[1] > marginal.view.size[1] * 2
    else:
        assert [cell.position for cell in canvas._cells] == [(0, 0), (0, 1)]
        assert main.view.size[1] == pytest.approx(marginal.view.size[1], abs=2)
        assert main.view.size[0] > marginal.view.size[0] * 2


def test_joint_grid_aligns_viewports_with_asymmetric_gutters(plot, qtbot, monkeypatch) -> None:
    from napari_plot import JointGrid

    monkeypatch.setattr("napari._vispy.layers.base.get_max_texture_sizes", lambda: (2048, 2048))
    viewer, canvas = plot
    JointGrid(viewer)
    main, top, right = canvas._cells
    assert main.position == (1, 0)
    # only the colorbar source: hidden, so no texture is uploaded (the macOS GL driver sometimes blocks on that upload)
    image = viewer.add_image(np.arange(9, dtype=float).reshape(3, 3), visible=False)
    _settle(qtbot, canvas)
    original_width, original_height = main.view.size

    viewer.set_legend([{"label": "Main plot line", "layer_name": "line 0", "color": "orange"}])
    viewer.legend.gridded = False
    viewer.legend.outside = True
    viewer.set_colorbar_from_layer(image, cell=main.position, position="bottom")
    _settle(qtbot, canvas)

    assert main.view.width < original_width
    assert main.view.height < original_height
    assert main.view.width == pytest.approx(top.view.width)
    assert main.view.height == pytest.approx(right.view.height)
    assert canvas._view_offset(main.view)[0] == pytest.approx(canvas._view_offset(top.view)[0])
    assert canvas._view_offset(main.view)[1] == pytest.approx(canvas._view_offset(right.view)[1])

    viewer.legend.outside = False
    viewer.clear_colorbar(cell=main.position)
    _settle(qtbot, canvas)
    assert main.view.size == pytest.approx((original_width, original_height))


def test_joint_grid_updates_panels_independently(make_napari_plot_viewer, qtbot, monkeypatch) -> None:
    from napari_plot import JointGrid

    monkeypatch.setattr("napari_plot._vispy.canvas.get_max_texture_sizes", lambda: (2048, 2048))
    viewer = make_napari_plot_viewer(show=True)
    canvas = viewer.window._qt_viewer.canvas
    canvas.native.setFixedSize(800, 600)
    main_layer = viewer.plot([0, 10], [0, 1])
    grid = JointGrid(viewer)
    top_layer = grid.add_layer(viewer.plot([0, 10], [1, 2]), panel="top")
    right_layer = grid.add_layer(viewer.plot([2, 3], [0, 10]), panel="right")
    viewer.reset_view()
    main, top, right = canvas._cells
    main_rect, top_rect, right_rect = (cell.camera.rect for cell in canvas._cells)

    top_layer.data = top_layer.data + [0, 100]
    assert top.camera.rect[2:] == pytest.approx(np.asarray(top_rect[2:]) + 100)
    assert main.camera.rect == pytest.approx(main_rect)
    assert right.camera.rect == pytest.approx(right_rect)

    right_layer.data = right_layer.data + [200, 0]
    assert right.camera.rect[:2] == pytest.approx(np.asarray(right_rect[:2]) + 200)
    assert main.camera.rect == pytest.approx(main_rect)
    assert top.camera.rect[2:] == pytest.approx(np.asarray(top_rect[2:]) + 100)

    main_layer.data = main_layer.data + [400, 300]
    _settle(qtbot, canvas)
    assert main.camera.rect[1] > 400
    assert main.camera.rect[3] > 300
    assert top.camera.rect[:2] == pytest.approx(main.camera.rect[:2])
    assert right.camera.rect[2:] == pytest.approx(main.camera.rect[2:])
    assert top.camera.rect[2:] == pytest.approx(np.asarray(top_rect[2:]) + 100)
    assert right.camera.rect[:2] == pytest.approx(np.asarray(right_rect[:2]) + 200)
    assert [canvas.layer_to_visual[layer].node.parent for layer in viewer.layers] == [
        cell.data_scene for cell in canvas._cells
    ]


def test_joint_grid_toggles_titles_per_panel(plot, qtbot) -> None:
    from napari_plot import JointGrid

    viewer, canvas = plot
    grid = JointGrid(viewer)
    grid.set_axis_labels("Time", "Response")
    grid.set_axis_labels(y_var="Count", panel="top", visible=False)
    grid.set_axis_labels(x_var="Density", panel="right")
    _settle(qtbot, canvas)
    main, top, right = canvas._cells
    top_axis = top.y_axis.node.axis
    right_axis = right.x_axis.node.axis

    assert top_axis.axis_label == "Count"
    assert not top_axis._axis_label_vis.visible
    assert top_axis._text.visible
    assert len(top_axis._text.text)
    assert right_axis.axis_label == "Density"
    assert right_axis._axis_label_vis.visible
    assert main.x_axis.node.axis._axis_label_vis.visible

    grid.set_axis_labels(visible=False)
    grid.set_axis_labels(panel="top", visible=True)
    _settle(qtbot, canvas)
    assert top_axis.axis_label == "Count"
    assert top_axis._axis_label_vis.visible
    assert not main.x_axis.node.axis._axis_label_vis.visible
    assert not main.y_axis.node.axis._axis_label_vis.visible
    assert right_axis._axis_label_vis.visible

    viewer.canvas.grid.enabled = False
    assert main.x_axis.node.axis._axis_label_vis.visible
    assert main.x_axis.node.axis.axis_label == "Time"


@pytest.fixture
def joint(make_napari_plot_viewer, qtbot, monkeypatch: pytest.MonkeyPatch):
    """Joint grid with autoscaled marginals: a main line, a peaked spectrum on top and a peaked profile on the right."""
    from napari_plot import JointGrid

    monkeypatch.setattr("napari_plot._vispy.canvas.get_max_texture_sizes", lambda: (2048, 2048))
    viewer = make_napari_plot_viewer(show=True)
    canvas = viewer.window._qt_viewer.canvas
    canvas.native.setFixedSize(800, 600)
    viewer.add_line(np.c_[[0, 10], [0, 10]], name="main")
    positions = np.linspace(0, 10, 101)
    peaked = np.where(positions >= 8, 50.0, 1.0)
    grid = JointGrid(viewer, autoscale=True)
    top = grid.add_layer(viewer.add_multi_line({"xs": [positions], "ys": [peaked, peaked / 2]}), panel="top")
    right = grid.add_layer(viewer.add_line(np.c_[2 * peaked, positions]), panel="right")
    viewer.reset_view()
    qtbot.waitUntil(lambda: canvas._cells[0].view.size[0] > 300)
    _settle(qtbot, canvas)
    return SimpleNamespace(viewer=viewer, canvas=canvas, grid=grid, top=top, right=right)


def test_joint_autoscale_fits_marginals_to_the_visible_range(joint, qtbot) -> None:
    viewer, canvas = joint.viewer, joint.canvas
    main, top, right = canvas._cells
    assert top.camera.rect[2:] == pytest.approx((0, 52.5))
    assert right.camera.rect[:2] == pytest.approx((0, 105))
    assert top.camera.camera.locked_axis == 1
    assert right.camera.camera.locked_axis == 0
    assert main.camera.camera.locked_axis is None

    viewer.camera.rect = (0, 5, 0, 5)
    assert top.camera.rect[2:] == pytest.approx((0, 1.05))
    assert right.camera.rect[:2] == pytest.approx((0, 2.1))
    assert top.camera.rect[:2] == pytest.approx((0, 5))
    assert right.camera.rect[2:] == pytest.approx((0, 5))

    # new data in view refits at once
    joint.top.data = {"xs": [np.linspace(0, 10, 101)], "ys": [np.full(101, 4.0)]}
    assert top.camera.rect[2:] == pytest.approx((0, 4.2))
    assert viewer.camera.rect == pytest.approx((0, 5, 0, 5))

    # panning the marginal moves the shared axis and refits its value axis
    start = _widget_center(canvas, top.view)
    _drag(canvas, start, start + (top.view.size[0] / 2, 0))
    assert viewer.camera.rect[:2] == pytest.approx((-2.5, 2.5), abs=0.05)
    assert top.camera.rect[2:] == pytest.approx((0, 4.2))

    viewer.canvas.grid.joint_autoscale = False
    assert top.camera.camera.locked_axis is None


def test_joint_autoscale_locks_interaction_in_marginals_to_the_shared_axis(joint, qtbot) -> None:
    from napari_plot.components.dragtool import DragMode

    viewer, canvas = joint.viewer, joint.canvas
    _main, top, right = canvas._cells
    viewer.camera.rect = (2, 6, 2, 6)

    # the wheel zooms only the shared axis, about the mouse
    canvas._scene_canvas.events.mouse_wheel(pos=tuple(_widget_center(canvas, top.view)), delta=(0, 1), modifiers=())
    x0, x1, y0, y1 = viewer.camera.rect
    assert x1 - x0 < 4
    assert (x0 + x1) / 2 == pytest.approx(4, abs=0.01)
    assert (y0, y1) == pytest.approx((2, 6))

    # a left drag zooms the shared axis, even with a selection tool
    selected = []
    viewer.events.selection.connect(selected.append)
    for mode in (DragMode.AUTO, DragMode.LASSO):
        viewer.drag_tool.active = mode
        viewer.camera.rect = (2, 6, 2, 6)
        offset, (width, height) = canvas._view_offset(right.view), right.view.size
        _drag(canvas, offset + (width / 2, height * 0.25), offset + (width * 0.6, height * 0.75), button=1)
        x0, x1, y0, y1 = viewer.camera.rect
        assert (x0, x1) == pytest.approx((2, 6))
        assert (y0, y1) == pytest.approx((3, 5), abs=0.05)
        assert viewer.drag_tool.panel == "right"
    assert not selected
    assert not viewer.drag_tool._box.visible

    # a double-click in the plot area shows the whole shared axis and keeps the other
    viewer.drag_tool.active = DragMode.AUTO
    viewer.camera.rect = (2, 6, 2, 6)
    _double_click(canvas, _widget_center(canvas, top.view))
    assert viewer.camera.rect[:2] == pytest.approx(viewer._get_rect_extent()[:2])
    assert viewer.camera.rect[2:] == pytest.approx((2, 6))


def _hover(canvas: VispyCanvas, pos: np.ndarray) -> None:
    """Move the mouse to the canvas position `pos`, without the throttling of the canvas."""
    from napari.utils.interactions import mouse_move_callbacks
    from vispy.app.canvas import MouseEvent

    canvas._process_mouse_event(mouse_move_callbacks, MouseEvent("mouse_move", pos=tuple(pos), modifiers=()))


def test_joint_events_report_their_panel(joint, qtbot) -> None:
    viewer, canvas = joint.viewer, joint.canvas
    panels = []
    viewer.mouse_move_callbacks.append(lambda _viewer, event: panels.append((event.joint_panel, event.joint_locked)))
    for cell in canvas._cells:
        _hover(canvas, _widget_center(canvas, cell.view))
    assert panels == [("joint", False), ("top", True), ("right", True)]
    viewer.canvas.grid.enabled = False
    assert canvas._joint_panel(canvas._cells[0]) is None


def test_joint_crosshair_draws_the_shared_line_in_marginals(joint, qtbot) -> None:
    viewer, canvas = joint.viewer, joint.canvas
    main, top, right = canvas._cells
    # gridded overlays get one visual per cell once they are shown
    viewer.crosshair.visible = True
    viewer.crosshair.show_coordinates = True
    viewer.mouse_over_canvas = True
    visuals = canvas._overlay_to_visual[viewer.crosshair]
    assert [visual.node.lines for visual in visuals] == [(True, True), (True, False), (False, True)]

    def hover(cell) -> None:
        _hover(canvas, _widget_center(canvas, cell.view))

    hover(main)
    x, y = viewer.crosshair.point
    assert np.isfinite([x, y]).all()
    # updating a layer keeps the crosshair where it is
    joint.top.data = {"xs": [np.linspace(0, 10, 11)], "ys": [np.ones(11)]}
    assert viewer.crosshair.point == pytest.approx((x, y))
    _settle(qtbot, canvas)
    assert len(visuals[0].node.pos) == 4
    assert len(visuals[1].node.pos) == 2
    assert visuals[1].node.pos[0][0] == pytest.approx(visuals[1].node.pos[1][0])  # vertical
    assert not visuals[1].node.label.visible

    # in a marginal only the shared coordinate is known
    hover(top)
    assert viewer.crosshair.point[0] == pytest.approx(x, abs=0.05)
    assert np.isnan(viewer.crosshair.point[1])
    hover(right)
    assert np.isnan(viewer.crosshair.point[0])

    viewer.canvas.grid.enabled = False
    assert canvas._overlay_to_visual[viewer.crosshair][0].node.lines == (True, True)


def test_joint_size_and_marginal_tick_formatters(joint, qtbot) -> None:
    viewer, canvas, grid = joint.viewer, joint.canvas, joint.grid
    main, top, right = canvas._cells

    def main_format(value: float) -> str:
        return f"main {value}"

    def top_format(value: float) -> str:
        return f"top {value}"

    viewer.axis.y_tick_formatter = main_format
    viewer.axis.x_tick_formatter = main_format
    _settle(qtbot, canvas)
    # the value axes of the marginals do not use the formatters of the main axes
    assert top.y_axis.node.axis.ticker.tick_format_func is None
    assert right.x_axis.node.axis.ticker.tick_format_func is None
    assert main.y_axis.node.axis.ticker.tick_format_func is main_format
    grid.set_tick_formatter(top_format, panel="top")
    assert top.y_axis.node.axis.ticker.tick_format_func is top_format
    assert right.x_axis.node.axis.ticker.tick_format_func is None

    viewer.canvas.grid.joint_size = 60
    _settle(qtbot, canvas)
    assert top.view.size[1] == pytest.approx(60, abs=1)
    assert right.view.size[0] == pytest.approx(60, abs=1)
    assert main.view.size[0] == pytest.approx(top.view.size[0], abs=2)
    assert main.view.size[1] == pytest.approx(right.view.size[1], abs=2)
    viewer.canvas.grid.joint_size = None
    _settle(qtbot, canvas)
    assert top.view.size[1] > 60


def _scene_rect(widget, root) -> tuple[float, float, float, float]:
    """(left, top, right, bottom) of a widget in the coordinates of its ancestor ``root``."""
    x, y = 0.0, 0.0
    node = widget
    while node is not root:
        x, y = x + node.pos[0], y + node.pos[1]
        node = node.parent
    return x, y, x + widget.size[0], y + widget.size[1]


def test_joint_size_keeps_marginals_flush_when_resizing(joint, qtbot) -> None:
    """With a fixed marginal size the main panel absorbs every resize; no blank space opens beside the marginals."""
    canvas = joint.canvas
    joint.viewer.canvas.grid.joint_size = 60
    main, top, right = canvas._cells
    cells_grid = canvas._cells_grid
    widths = []
    for size in ((800, 600), (1200, 900), (700, 500)):
        canvas.native.setFixedSize(*size)
        qtbot.waitUntil(lambda size=size: canvas._scene_canvas.size == size)
        _settle(qtbot, canvas)
        cells_grid._prepare_draw(cells_grid)
        for cell in (main, top, right):
            cell.layout._prepare_draw(cell.layout)
        assert top.view.size[1] == pytest.approx(60, abs=1)
        assert right.view.size[0] == pytest.approx(60, abs=1)
        spacing = cells_grid.spacing[1] if isinstance(cells_grid.spacing, tuple) else cells_grid.spacing
        top_rect, main_rect, right_rect = (_scene_rect(cell.view, cells_grid) for cell in (top, main, right))
        # the top marginal sits right above the heatmap and the right marginal ends at the edge of the plot area
        assert main_rect[1] - top_rect[3] == pytest.approx(spacing, abs=1)
        assert right_rect[2] == pytest.approx(cells_grid.size[0], abs=1)
        assert main_rect[0] == pytest.approx(top_rect[0], abs=1)
        assert main_rect[2] == pytest.approx(top_rect[2], abs=1)
        widths.append(main.view.size[0])
    assert widths[1] > widths[0] > widths[2]


def test_joint_autoscale_follows_streamed_marginal_data(joint) -> None:
    """Streaming new data into a marginal refits its value axis without touching the main view."""
    viewer, canvas = joint.viewer, joint.canvas
    _, top, _ = canvas._cells
    viewer.camera.rect = (0, 5, 0, 5)
    main_rect = viewer.camera.rect
    assert top.camera.rect[2:] == pytest.approx((0, 1.05))

    positions = np.linspace(0, 10, 51)
    joint.top.stream({"xs": [positions], "ys": [np.full(51, 4.0), np.full(51, 2.0)]})
    assert top.camera.rect[2:] == pytest.approx((0, 4.2))
    assert top.camera.rect[:2] == pytest.approx((0, 5))
    assert viewer.camera.rect == pytest.approx(main_rect)

    # values beyond the data the panel had before (the cached layer extent must not limit the fit)
    joint.top.stream({"xs": [positions], "ys": [np.full(51, 400.0), np.full(51, 2.0)]})
    assert top.camera.rect[2:] == pytest.approx((0, 420))

    # with all the data in view the fit keeps its headroom above the largest value
    viewer.camera.rect = (0, 10, 0, 10)
    assert top.camera.rect[2:] == pytest.approx((0, 420))


def test_grid_blends_the_bottom_layer_of_each_cell_with_its_background(joint) -> None:
    """Each plot cell has its own bottom layer, which napari blends with the background (e.g. additive stays visible)."""
    viewer, canvas = joint.viewer, joint.canvas
    main_layer = viewer.layers["main"]
    # a marginal layer at the bottom of the layer list must not take that role in the main cell
    viewer.layers.move(viewer.layers.index(joint.top), 0)
    first = {layer.name: canvas.layer_to_visual[layer].first_visible for layer in viewer.layers}
    assert first == {joint.top.name: True, "main": True, joint.right.name: True}

    viewer.add_line(np.c_[[0, 10], [5, 5]], name="second")  # drawn above "main" in the main cell
    assert not canvas.layer_to_visual[viewer.layers["second"]].first_visible
    main_layer.visible = False
    assert canvas.layer_to_visual[viewer.layers["second"]].first_visible
