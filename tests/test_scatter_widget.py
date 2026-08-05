"""Test ScatterPlotWidget"""

import numpy as np
import pytest
from napari.layers import Image, Shapes

from napari_plot._scatter_widget import ScatterPlotWidget


def test_scatter_init(make_napari_viewer, qtbot):
    """The last two images are selected and their full 2D slices are paired."""
    viewer = make_napari_viewer(strict_qt=False)
    first = viewer.add_image(np.arange(100).reshape(10, 10), name="first")
    second = viewer.add_image(np.arange(100, 200).reshape(10, 10), name="second")
    widget = ScatterPlotWidget(viewer)
    qtbot.addWidget(widget)

    assert len(widget.layers) == 2
    np.testing.assert_array_equal(widget.scatter_layer.data[:, 0], second.data.ravel())
    np.testing.assert_array_equal(widget.scatter_layer.data[:, 1], first.data.ravel())


def test_scatter_select_event(make_napari_viewer, qtbot):
    """Selecting two images updates the scatter widget."""
    viewer = make_napari_viewer(strict_qt=False)
    widget = ScatterPlotWidget(viewer)
    qtbot.addWidget(widget)
    assert len(widget.layers) == 0
    viewer.add_image(np.random.random((10, 10)))
    viewer.add_image(np.random.random((10, 10)))
    viewer.layers.select_all()
    assert len(widget.layers) == 2


def test_scatter_diff_shape(make_napari_viewer, qtbot):
    """Mismatched displayed slices are rejected instead of truncated."""
    viewer = make_napari_viewer(strict_qt=False)
    widget = ScatterPlotWidget(viewer)
    qtbot.addWidget(widget)
    assert len(widget.layers) == 0
    viewer.add_image(np.random.random((10, 10)))
    viewer.add_image(np.random.random((100, 100)))
    with pytest.warns(UserWarning, match="matching displayed-slice shapes"):
        viewer.layers.select_all()
    assert len(widget.layers) == 2
    assert len(widget.scatter_layer.data) == 0


def test_scatter_select_good_layer(make_napari_viewer, qtbot):
    """Non-image selections clear the scatter widget selection."""
    viewer = make_napari_viewer(strict_qt=False)
    widget = ScatterPlotWidget(viewer)
    qtbot.addWidget(widget)
    assert len(widget.layers) == 0
    viewer.add_image(np.random.random((10, 10)))
    viewer.add_shapes(None)
    viewer.layers.select_all()
    assert len(widget.layers) == 0


def test_scatter_uses_current_nd_slice(make_napari_viewer, qtbot):
    """Changing a non-displayed dimension updates paired values."""
    viewer = make_napari_viewer(strict_qt=False)
    first = viewer.add_image(np.arange(24).reshape(2, 3, 4))
    second = viewer.add_image(np.arange(100, 124).reshape(2, 3, 4))
    widget = ScatterPlotWidget(viewer)
    qtbot.addWidget(widget)

    viewer.dims.set_current_step(0, 1)
    qtbot.waitUntil(lambda: np.array_equal(first._data_view, first.data[1]))
    widget.on_update_scatter()

    np.testing.assert_array_equal(widget.scatter_layer.data[:, 0], second.data[1].ravel())
    np.testing.assert_array_equal(widget.scatter_layer.data[:, 1], first.data[1].ravel())
    assert widget.current_slice_label == "0=1"


def test_check_layers_accepts_image_subclasses():
    """Image subclasses should be valid scatter inputs."""

    class ImageSubclass(Image):
        pass

    layers = [ImageSubclass(np.zeros((2, 2))), Image(np.ones((2, 2)))]
    assert ScatterPlotWidget._check_layers(layers)
    assert not ScatterPlotWidget._check_layers([layers[0], Shapes()])
