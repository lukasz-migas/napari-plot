"""Exercise interval visuals and native vectors through the Qt viewer."""

import numpy as np
import pytest
from napari.layers import Vectors

from napari_plot._qt.qt_layer_buttons import _add_empty_layer


def test_band_controls_and_visual_updates(make_napari_plot_viewer) -> None:
    """An empty band can be styled, filled, cleared, and hidden."""
    viewer = make_napari_plot_viewer()
    qt_viewer = viewer.window._qt_viewer
    layer = _add_empty_layer(viewer, "Band")
    controls = qt_viewer.controls.widgets[layer]
    node = qt_viewer.canvas.layer_to_visual[layer].node
    assert not node.visible

    layer.data = [[1, -1, 0], [3, 1, 0]]
    assert node.visible
    assert node.mesh_data.get_vertices().shape == (6, 2)
    controls.fill_color_swatch.set_color("red")
    np.testing.assert_array_equal(layer.fill_color, [1, 0, 0, 1])
    np.testing.assert_array_equal(node.color.rgba, [1, 0, 0, 1])
    layer.fill_color = "blue"
    np.testing.assert_array_equal(controls.fill_color_swatch.color, [0, 0, 1, 1])
    controls.opacity_slider.setValue(50)
    assert node.opacity == pytest.approx(0.5)

    layer.visible = False
    layer.data = [[1, 0, 2], [3, 0, 2]]
    assert not node.visible
    layer.visible = True
    assert node.visible
    layer.data = None
    assert not node.visible


def test_areas_controls_and_visual_updates(make_napari_plot_viewer) -> None:
    """An empty areas layer can be filled, outlined, and cleared."""
    viewer = make_napari_plot_viewer()
    qt_viewer = viewer.window._qt_viewer
    layer = _add_empty_layer(viewer, "Areas")
    controls = qt_viewer.controls.widgets[layer]
    node = qt_viewer.canvas.layer_to_visual[layer].node
    assert not node.mesh.visible

    layer.data = [[[0, 0, 1], [1, 0, 2]], [[2, 0, 1], [3, 0, 1]]]
    assert node.mesh.visible
    assert node.border.visible
    assert node.mesh.mesh_data.get_vertices().shape[0] == 12
    controls.border_width_spinbox.setValue(0)
    assert layer.border_width == 0
    assert not node.border.visible
    layer.border_width = 2
    assert controls.border_width_spinbox.value() == 2

    layer.data = None
    assert not node.mesh.visible


def test_error_bar_controls_and_visual_updates(make_napari_plot_viewer) -> None:
    """Error bar controls synchronize style and accept empty geometry."""
    viewer = make_napari_plot_viewer()
    qt_viewer = viewer.window._qt_viewer
    layer = _add_empty_layer(viewer, "ErrorBar")
    controls = qt_viewer.controls.widgets[layer]
    node = qt_viewer.canvas.layer_to_visual[layer].node
    assert node._count == 0

    layer.data = [[1, 2, np.nan, np.nan, 2, 3]]
    assert node._count == 1
    controls.width_spinbox.setValue(2)
    controls.cap_size_spinbox.setValue(0)
    assert layer.width == node._width == 2
    assert layer.cap_size == node._cap_size == 0
    controls.color_swatch.set_color("red")
    np.testing.assert_array_equal(layer.color, [1, 0, 0, 1])
    layer.color = "blue"
    np.testing.assert_array_equal(controls.color_swatch.color, [0, 0, 1, 1])
    layer.width = 3
    layer.cap_size = 8
    assert controls.width_spinbox.value() == 3
    assert controls.cap_size_spinbox.value() == 8
    layer.data = None
    assert node._count == 0


def test_vectors_overlay_updates_in_qt_viewer(make_napari_plot_viewer) -> None:
    """Native arrows overlay an image in the expected order and units."""
    viewer = make_napari_plot_viewer()
    qt_viewer = viewer.window._qt_viewer
    viewer.add_image(np.zeros((15, 20)), units=("um", "um"))
    vectors = viewer.add_vectors(np.array([[[3, 8], [4, -2]]]), units=("um", "um"), vector_style="arrow", length=1)
    assert isinstance(vectors, Vectors)
    assert vectors in qt_viewer.controls.widgets
    node = qt_viewer.canvas.layer_to_visual[vectors].node

    def check_endpoint(x: float, y: float) -> None:
        vertices = node.mesh_data.get_vertices()[:, :2]
        assert np.isclose(vertices, [x, y]).all(axis=1).any()

    check_endpoint(6, 7)
    vectors.length = 2
    check_endpoint(4, 11)
    vectors.visible = False
    assert not node.visible
    vectors.visible = True
    assert node.visible


def test_error_bar_caps_keep_pixel_size_during_zoom(make_napari_plot_viewer) -> None:
    """Rendered cap length stays constant as the stem changes screen length."""
    viewer = make_napari_plot_viewer(show=True)
    layer = viewer.errorbar([0], [0], yerr=1, color="red", width=2, cap_size=12)
    canvas = viewer.window._qt_viewer.canvas
    canvas.native.setFixedSize(360, 280)

    def red_pixels() -> np.ndarray:
        pixels = canvas._scene_canvas.render()
        return (pixels[..., 0] > 200) & (pixels[..., 1] < 64)

    cap_widths = []
    stem_heights = []
    for half_range in (4, 2):
        viewer.camera.rect = (-half_range, half_range, -half_range, half_range)
        red = red_pixels()
        cap_widths.append(np.count_nonzero(red, axis=1).max())
        stem_heights.append(np.count_nonzero(red, axis=0).max())
    pixel_scale = canvas._scene_canvas.pixel_scale
    assert cap_widths[0] == cap_widths[1] == pytest.approx(12 * pixel_scale, abs=1)
    assert stem_heights[1] > stem_heights[0]
    layer.cap_size = 0
    assert np.count_nonzero(red_pixels(), axis=1).max() == pytest.approx(2 * pixel_scale, abs=1)
