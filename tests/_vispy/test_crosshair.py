"""Crosshair and hover readout visuals."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from napari_plot import Viewer


@pytest.mark.parametrize("scale", ["linear", "log"])
def test_crosshair_goes_through_data_point(make_napari_plot_viewer: Callable[[], Viewer], scale: str) -> None:
    """The lines cross at the data point in every plot cell, on linear and log axes."""
    viewer = make_napari_plot_viewer()
    for _ in range(2):  # grid mode gives each layer a cell
        viewer.add_line(np.c_[np.arange(1.0, 11.0), np.arange(1.0, 11.0)])
    viewer.axis.x_scale = scale
    canvas = viewer.window._qt_viewer.canvas
    canvas._scene_canvas.central_widget.size = (800, 600)
    viewer.camera.rect = (1.0, 10.0, 0.0, 10.0)
    viewer.canvas.grid.enabled = True
    viewer.crosshair.visible = True
    viewer.crosshair.point = (5.0, 4.0)

    visuals = canvas._overlay_to_visual[viewer.crosshair]
    assert len(visuals) == len(canvas._cells) > 1
    for visual, cell in zip(visuals, canvas._cells, strict=True):
        node = visual.node
        assert node._prepare_draw(node) is not False
        expected = cell.data_scene.node_transform(cell.view).map([[5.0, 4.0]])[0, :2]
        vertical, horizontal = node.pos[:2], node.pos[2:]
        np.testing.assert_allclose(vertical[:, 0], expected[0], rtol=1e-5)
        np.testing.assert_allclose(horizontal[:, 1], expected[1], rtol=1e-5)
        assert node.label.text == "x=5, y=4"

    viewer.crosshair.show_coordinates = False
    node = visuals[0].node
    node._prepare_draw(node)
    assert not node.label.visible
    viewer.crosshair.point = None
    assert node._prepare_draw(node) is False


def test_hover_box_hides_without_text(make_napari_plot_viewer: Callable[[], Viewer]) -> None:
    """The readout box only shows while it has text."""
    viewer = make_napari_plot_viewer()
    visual = viewer.window._qt_viewer.canvas._overlay_to_visual[viewer.hover][0]
    viewer.hover.visible = True
    assert not visual.node.visible
    viewer.hover.text = "x: 1\ny: 2"
    assert visual.node.visible
    viewer.hover.text = ""
    assert not visual.node.visible

    viewer.hover.text = "x: 1"
    viewer.hover.box_padding = (12, 6)
    assert visual.box_padding == (12, 6)
    assert visual.box.width == pytest.approx(visual.x_size + 24)
