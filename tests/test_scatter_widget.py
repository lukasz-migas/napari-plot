"""Test ScatterPlotWidget"""

import numpy as np
import pytest

from napari_plot._scatter_widget import ScatterPlotWidget


@pytest.mark.xfail
def test_scatter_init(make_napari_viewer):
    # Check that two images are automatically selected
    viewer = make_napari_viewer(strict_qt=False)
    viewer.add_image(np.random.random((10, 10)))
    viewer.add_image(np.random.random((10, 10)))
    widget = ScatterPlotWidget(viewer)
    assert len(widget.layers) == 2


@pytest.mark.xfail
def test_scatter_select_event(make_napari_viewer):
    # Check that two images are automatically selected
    viewer = make_napari_viewer(strict_qt=False)
    widget = ScatterPlotWidget(viewer)
    assert len(widget.layers) == 0
    viewer.add_image(np.random.random((10, 10)))
    viewer.add_image(np.random.random((10, 10)))
    viewer.layers.select_all()
    assert len(widget.layers) == 2


@pytest.mark.xfail
def test_scatter_diff_shape(make_napari_viewer):
    # Check that two images are automatically selected
    viewer = make_napari_viewer(strict_qt=False)
    widget = ScatterPlotWidget(viewer)
    assert len(widget.layers) == 0
    viewer.add_image(np.random.random((10, 10)))
    viewer.add_image(np.random.random((100, 100)))
    viewer.layers.select_all()
    assert len(widget.layers) == 2


@pytest.mark.xfail
def test_scatter_select_good_layer(make_napari_viewer):
    # Check that two images are automatically selected
    viewer = make_napari_viewer(strict_qt=False)
    widget = ScatterPlotWidget(viewer)
    assert len(widget.layers) == 0
    viewer.add_image(np.random.random((10, 10)))
    viewer.add_shapes(None)
    viewer.layers.select_all()
    assert len(widget.layers) == 0
