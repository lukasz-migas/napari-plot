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
