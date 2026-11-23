"""Compare rendered plot and overlay pixels against geometry-based references."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest
from qtpy.QtWidgets import QApplication

if TYPE_CHECKING:
    from napari_plot._vispy.canvas import VispyCanvas


@pytest.fixture
def rendered_plot(make_napari_plot_viewer, qtbot):
    """Create a fixed size render surface using the native OpenGL backend."""
    viewer = make_napari_plot_viewer(show=True)
    canvas = viewer.window._qt_viewer.canvas
    canvas.native.setFixedSize(600, 400)
    viewer.canvas.background_color_override = "black"
    qtbot.waitUntil(lambda: min(canvas.view.size) > 1)
    return viewer, canvas


def _render(canvas: VispyCanvas) -> tuple[np.ndarray, np.ndarray]:
    QApplication.processEvents()
    image = canvas._scene_canvas.render()[..., :3]
    scale = np.array(image.shape[1::-1]) / np.array(canvas._scene_canvas.size)
    return image, scale


def _color_mask(image: np.ndarray, color: tuple[int, int, int]) -> np.ndarray:
    return np.all(abs(image.astype(np.int16) - np.asarray(color)) < 20, axis=-1)


def test_filled_band_image_matches_rectangle(rendered_plot) -> None:
    """The band fills the expected data rectangle with the selected color."""
    viewer, canvas = rendered_plot
    viewer.add_band([[2, 2, 6], [6, 2, 6]], fill_color="red", opacity=1.0)
    viewer.camera.rect = (0, 8, 0, 8)
    image, scale = _render(canvas)

    left, top = canvas._view_offset(canvas.view) * scale
    width, height = np.asarray(canvas.view.size) * scale
    row, col = np.ogrid[: image.shape[0], : image.shape[1]]
    expected = (
        (col + 0.5 >= left + width / 4)
        & (col + 0.5 < left + 3 * width / 4)
        & (row + 0.5 >= top + height / 4)
        & (row + 0.5 < top + 3 * height / 4)
    )
    actual = _color_mask(image, (255, 0, 0))
    assert np.count_nonzero(expected & actual) / np.count_nonzero(expected | actual) > 0.97


def test_text_overlay_moves_without_changing_image(rendered_plot) -> None:
    """An overlay moving between top corners translates the same rendered text and box."""
    viewer, canvas = rendered_plot
    viewer.add_line([[0, 0], [1, 1]], visible=False)
    overlay = viewer.add_text_overlay("Plot", position="top_left", box=True, box_color="magenta", color="black")

    def crop() -> tuple[np.ndarray, int, int, np.ndarray]:
        image, scale = _render(canvas)
        rows, cols = np.where(_color_mask(image, (255, 0, 255)))
        assert rows.size > 40
        top, left = rows.min(), cols.min()
        cropped = image[top : rows.max() + 1, left : cols.max() + 1]
        return cropped, top, left, scale

    original, top, left, scale = crop()
    assert np.any(original[..., 0] < 128)  # glyphs are drawn over the magenta box
    overlay.position = "top_right"
    moved, moved_top, moved_left, _ = crop()
    padding = viewer.canvas.overlay_tiling.padding[0]
    expected_shift = canvas.view.size[0] * scale[0] - original.shape[1] - 2 * padding * scale[0]
    assert moved_left - left == pytest.approx(expected_shift, abs=8 * scale[0])
    assert moved_top == pytest.approx(top, abs=1)
    assert abs(moved.shape[0] - original.shape[0]) <= 1
    assert abs(moved.shape[1] - original.shape[1]) <= 1
    height = min(moved.shape[0], original.shape[0])
    width = min(moved.shape[1], original.shape[1])
    delta = abs(moved[:height, :width].astype(float) - original[:height, :width]).mean()
    assert delta < 15


def test_colorbar_image_matches_colormap(rendered_plot) -> None:
    """The left-to-right colorbar pixels follow the requested colormap."""
    viewer, canvas = rendered_plot
    layer = viewer.add_image(np.arange(9).reshape(3, 3), colormap="viridis", contrast_limits=(0, 8))
    bar = viewer.set_colorbar_from_layer(layer, position="bottom")
    image, scale = _render(canvas)
    gradient = canvas.colorbar._bar.img
    origin = canvas._view_offset(canvas.colorbar.node) + gradient.transform.translate[:2]
    width, height = gradient.size * gradient.transform.scale[:2]
    fractions = np.array([0.15, 0.5, 0.85])
    points = ((origin + np.column_stack((width * fractions, np.full(3, height / 2)))) * scale).astype(int)
    actual = image[points[:, 1], points[:, 0]]
    expected = 255 * bar.colormap.map(fractions)[:, :3]
    np.testing.assert_allclose(actual, expected, atol=10)


def test_line_dashes_are_visible_at_unit_data_scale(rendered_plot) -> None:
    """Dash gaps are measured in pixels even when data spans less than a unit."""
    viewer, canvas = rendered_plot
    line = viewer.plot([0.1, 0.9], [0.5, 0.5], color="red", width=3, dashes=(5, 4))
    viewer.camera.rect = (0, 1, 0, 1)
    image, _ = _render(canvas)
    dashed_columns = np.any(_color_mask(image, (255, 0, 0)), axis=0)
    line.dashes = None
    image, _ = _render(canvas)
    solid_columns = np.any(_color_mask(image, (255, 0, 0)), axis=0)
    assert solid_columns.sum() > 100
    assert 0.3 < dashed_columns.sum() / solid_columns.sum() < 0.9
