"""Tests for the concise plotting facade."""

import runpy
from pathlib import Path

import numpy as np
import pytest
from napari.layers import Image

import napari_plot
from napari_plot.components.viewer_model import ViewerModel
from napari_plot.layers import Bar, Line, Scatter


def test_plot_accepts_y_or_x_y() -> None:
    viewer = ViewerModel()

    generated = viewer.plot([3, 5, 4], name="generated")
    explicit = viewer.plot([10, 20], [1, 2], color="red")

    assert isinstance(generated, Line)
    np.testing.assert_array_equal(generated.data, [[0, 3], [1, 5], [2, 4]])
    np.testing.assert_array_equal(explicit.data, [[10, 1], [20, 2]])


def test_scatter_uses_conventional_x_y_arguments() -> None:
    viewer = ViewerModel()

    layer = viewer.scatter([10, 20], [1, 2])

    assert isinstance(layer, Scatter)
    np.testing.assert_array_equal(layer.data, [[1, 10], [2, 20]])


def test_plotting_facade_rejects_mismatched_coordinates() -> None:
    viewer = ViewerModel()

    with pytest.raises(ValueError, match="same shape"):
        viewer.plot([1, 2], [3])
    with pytest.raises(ValueError, match="one-dimensional"):
        viewer.scatter([[1, 2]])


def test_imshow_adds_image() -> None:
    viewer = ViewerModel()
    data = np.arange(9).reshape(3, 3)

    layer = viewer.imshow(data, name="image")

    assert isinstance(layer, Image)
    np.testing.assert_array_equal(layer.data, data)


def test_bar_helpers_set_orientation_and_positions() -> None:
    viewer = ViewerModel()

    vertical = viewer.vbar([2, 4])
    horizontal = viewer.hbar([10, 20], [3, 5])

    assert isinstance(vertical, Bar)
    assert vertical.orientation == "vertical"
    np.testing.assert_array_equal(vertical.data, [[0, 2], [1, 4]])
    assert horizontal.orientation == "horizontal"
    np.testing.assert_array_equal(horizontal.data, [[10, 3], [20, 5]])


def test_documented_bar_and_legend_example_executes(monkeypatch: pytest.MonkeyPatch) -> None:
    """The documented Bar and legend workflow stays executable without a GUI."""
    monkeypatch.setattr(napari_plot, "Viewer", ViewerModel)
    monkeypatch.setattr(napari_plot, "run", lambda: None)
    example = Path(__file__).parent.parent / "examples" / "add_bars_and_legend.py"

    namespace = runpy.run_path(str(example))

    viewer = namespace["viewer1d"]
    assert len(viewer.layers) == 2
    assert viewer.legend.visible is True


def test_reference_lines_spans_and_rectangle() -> None:
    viewer = ViewerModel()
    assert viewer.axhline(3).orientation == ["horizontal"]
    assert viewer.axvline(4).orientation == ["vertical"]
    assert viewer.axhspan(1, 3).orientation == ["horizontal"]
    assert viewer.axvspan(2, 4).orientation == ["vertical"]
    np.testing.assert_array_equal(viewer.rectangle((1, 2), 4, 6, color="red").data, [[3, 5, 6, 4]])


def test_text_annotation_and_stems() -> None:
    viewer = ViewerModel()
    label = viewer.annotate("peak", (1, 4), (2, 6))
    np.testing.assert_array_equal(label.data, [[2, 6]])
    assert label.text.tolist() == ["peak"]
    arrow = viewer.layers[-1]
    np.testing.assert_array_equal(arrow.data[:2], [[2, 6], [1, 4]])
    np.testing.assert_array_equal(viewer.stem([2, 3], baseline=1).data, [[0, 1, 2], [1, 1, 3]])


def test_horizontal_fill_histogram_and_stacked_areas() -> None:
    viewer = ViewerModel()
    band = viewer.fill_betweenx([10, 20], [3, 4], 1, color="blue")
    np.testing.assert_array_equal(band.extent.data, [[10, 1], [20, 4]])
    assert band.orientation == "horizontal"
    histogram = viewer.hist([0, 0.5, 1, 2], bins=[0, 1, 3], baseline=2)
    np.testing.assert_array_equal(histogram.data, [[0.5, 4, 2, 1], [2, 4, 2, 2]])
    stacked = viewer.stackplot([0, 1], [2, 3], [3, 4])
    np.testing.assert_array_equal(stacked.data[1], [[0, 2, 5], [1, 3, 7]])


def test_hbar_width_disambiguates_thickness_and_legacy_lengths() -> None:
    viewer = ViewerModel()
    layer = viewer.hbar([4, 8], [10, 12], width=0.3, baseline=2, color="red")
    assert layer.width == 0.3
    assert layer.baseline == 2
    np.testing.assert_array_equal(layer.data, [[4, 10], [8, 12]])
    np.testing.assert_array_equal(viewer.hbar([1, 2], width=[5, 6]).data, [[1, 5], [2, 6]])
    assert viewer.vbar([1, 2], bottom=2).baseline == 2
