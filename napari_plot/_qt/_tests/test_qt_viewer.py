"""Check QtViewer"""
import numpy as np
import pytest

from napari_plot._tests.utils import add_layer_by_type, layer_test_data, skip_on_win_ci


def test_qt_viewer(make_napari_plot_viewer):
    """Test instantiating viewer."""
    viewer = make_napari_plot_viewer()
    view = viewer.window._qt_viewer

    assert viewer.title == "napari-plot"
    assert view.viewer == viewer

    assert len(viewer.layers) == 0
    assert view.layers.model().rowCount() == 0


@pytest.mark.parametrize("layer_class, data", layer_test_data)
def test_add_layer(make_napari_plot_viewer, layer_class, data):

    viewer = make_napari_plot_viewer()
    add_layer_by_type(viewer, layer_class, data)


@skip_on_win_ci
def test_screenshot(make_napari_plot_viewer):
    "Test taking a screenshot"
    viewer = make_napari_plot_viewer()

    np.random.seed(0)
    # Add points
    data = 20 * np.random.random((10, 2))
    viewer.add_points(data)

    # Add shapes
    data = 20 * np.random.random((10, 4, 2))
    viewer.add_shapes(data)

    # Take screenshot
    screenshot = viewer.window.screenshot(flash=False, canvas_only=False)
    assert screenshot.ndim == 3
    screenshot = viewer.window.screenshot(flash=False, canvas_only=True)
    assert screenshot.ndim == 3


def test_remove_points(make_napari_plot_viewer):
    viewer = make_napari_plot_viewer()
    viewer.add_points([(1, 2), (2, 3)])
    del viewer.layers[0]
    viewer.add_points([(1, 2), (2, 3)])
