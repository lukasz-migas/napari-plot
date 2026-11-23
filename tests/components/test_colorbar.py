"""Tests for the colorbar model and its link to image layers."""

from __future__ import annotations

import numpy as np

from napari_plot.components.colorbar import ColorBar
from napari_plot.components.viewer_model import ViewerModel


def test_colorbar_defaults_and_colormap_coercion() -> None:
    """The colorbar is hidden by default and accepts colormap names."""
    colorbar = ColorBar()
    assert colorbar.visible is False

    colorbar.colormap = "magma"
    assert colorbar.colormap.name == "magma"


def test_colorbar_follows_layer_until_removed() -> None:
    """The colorbar copies the layer's colormap and limits, and is hidden when the layer goes away."""
    viewer = ViewerModel()
    layer = viewer.add_image(np.arange(12, dtype=float).reshape(3, 4), colormap="viridis", contrast_limits=(0, 11))

    viewer.set_colorbar_from_layer(layer, label="Intensity")
    assert viewer.colorbar.visible
    assert viewer.colorbar.label == "Intensity"
    assert viewer.colorbar.contrast_limits == (0.0, 11.0)

    layer.colormap = "magma"
    layer.contrast_limits = (2, 5)
    assert viewer.colorbar.colormap.name == "magma"
    assert viewer.colorbar.contrast_limits == (2.0, 5.0)

    viewer.layers.remove(layer)
    assert not viewer.colorbar.visible
    layer.contrast_limits = (0, 1)
    assert viewer.colorbar.contrast_limits == (2.0, 5.0)


def test_reset_plot_hides_colorbar() -> None:
    """Resetting the plot hides the colorbar."""
    viewer = ViewerModel()
    viewer.set_colorbar_from_layer(viewer.add_image(np.eye(3)))

    viewer.reset_plot()

    assert not viewer.colorbar.visible


def test_heatmap_cbar_shows_colorbar() -> None:
    """``heatmap(cbar=True)`` shows a colorbar with the heatmap limits."""
    viewer = ViewerModel()
    viewer.heatmap(np.array([[0.0, 1.0], [2.0, 3.0]]), vmin=0, vmax=3, cbar=True)

    assert viewer.colorbar.visible
    assert viewer.colorbar.contrast_limits == (0.0, 3.0)


def test_colorbar_widens_canvas_column(make_napari_plot_viewer) -> None:
    """Showing the colorbar widens the column right of the plot; hiding it restores the padding."""
    viewer = make_napari_plot_viewer()
    canvas = viewer.window._qt_viewer.canvas
    padding = canvas._scene_canvas.padding_x
    default = padding.width_max

    viewer.colorbar.label = "Value"
    viewer.colorbar.visible = True
    assert padding.width_max > default
    assert canvas.colorbar.node.visible
    assert canvas.colorbar.axis.axis_label == "Value"

    viewer.colorbar.visible = False
    assert padding.width_max == default
    assert not canvas.colorbar.node.visible


def test_scatter_colorbar_follow_and_cell_independence() -> None:
    """Follow the Scatter face properties without changing the figure colorbar."""
    viewer = ViewerModel()
    scatter = viewer.add_scatter(
        [[1, 2], [3, 4]],
        features={"intensity": [1, 100]},
        face_color="intensity",
        face_contrast_limits=(1, 100),
        face_colormap="magma",
    )
    bar = viewer.set_colorbar_from_layer(scatter, cell=(1, 0), norm="log", orientation="horizontal")
    assert bar is viewer.colorbar_for_cell(1, 0)
    assert bar.position == "bottom"
    assert bar.norm == "log"
    assert bar.contrast_limits == (1, 100)
    assert bar.colormap.name == "magma"
    assert not viewer.colorbar.visible
    scatter.face_colormap = "viridis"
    scatter.face_contrast_limits = (10, 1000)
    assert bar.colormap.name == "viridis"
    assert bar.contrast_limits == (10, 1000)
    viewer.layers.remove(scatter)
    assert not bar.visible


def test_horizontal_log_colorbar_renders_in_grid_cell(make_napari_plot_viewer) -> None:
    viewer = make_napari_plot_viewer()
    canvas = viewer.window._qt_viewer.canvas
    image = viewer.add_image(np.arange(1.0, 13.0).reshape(3, 4), contrast_limits=(1, 100))
    viewer.canvas.grid.enabled = True
    bar = viewer.set_colorbar_from_layer(image, cell=(0, 0), position="bottom", norm="log")
    visual = canvas._cell_colorbars[(0, 0)]
    assert visual.node.parent is canvas._cells[0].layout
    assert visual.axis.scale_type == "logarithmic"
    assert visual.axis.domain == (0, 2)
    assert canvas.colorbar.node.parent is None
    bar.position = "right"
    np.testing.assert_allclose(visual.axis.tick_direction, (1, 0))
    viewer.canvas.grid.enabled = False
    assert visual.node.parent is None
    assert bar.visible
