"""Tests for the canvas grid mode: one plot cell per layer group with synchronized cameras."""

from __future__ import annotations

import gc
from types import SimpleNamespace
from typing import TYPE_CHECKING

import numpy as np
import pytest
from qtextra.widgets.qt_toolbar_mini import QtMiniToolbar
from qtpy.QtCore import QPoint, Qt

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
