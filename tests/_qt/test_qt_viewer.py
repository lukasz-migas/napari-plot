"""Check QtViewer"""

import numpy as np
import pytest
from qtpy.QtWidgets import QVBoxLayout, QWidget

from napari_plot._qt._qapp_model._qproviders import _provide_qt_viewer, _provide_viewer
from napari_plot._qt.qt_viewer import QtViewer
from napari_plot.components.viewer_model import ViewerModel
from napari_plot.utils._test_support import add_layer_by_type, layer_test_data, skip_on_win_ci


def test_qt_viewer(make_napari_plot_viewer):
    """Test instantiating viewer."""
    viewer = make_napari_plot_viewer()
    view = viewer.window._qt_viewer

    assert viewer.title == "napari-plot"
    assert view.viewer == viewer

    assert len(viewer.layers) == 0
    assert view.layers.model().rowCount() == 0


def test_qt_viewer_with_console(make_napari_plot_viewer):
    """Test instantiating console from viewer."""
    viewer = make_napari_plot_viewer()
    view = viewer.window._qt_viewer
    # Check console is created when requested
    assert view.console is not None
    assert view.dockConsole.widget() is view.console


def test_qt_viewer_toggle_console(make_napari_plot_viewer):
    """Test instantiating console from viewer."""
    viewer = make_napari_plot_viewer()
    view = viewer.window._qt_viewer
    # Check console has been created when it is supposed to be shown
    view.on_toggle_console_visibility(None)
    assert view._console is not None
    assert view.dockConsole.widget() is view.console


@pytest.mark.parametrize(("layer_class", "data"), layer_test_data)
def test_add_layer(make_napari_plot_viewer, layer_class, data):
    viewer = make_napari_plot_viewer()
    add_layer_by_type(viewer, layer_class, data)


@skip_on_win_ci
def test_screenshot(make_napari_plot_viewer):
    "Test taking a screenshot"
    viewer = make_napari_plot_viewer()

    np.random.default_rng(0)
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


# @skip_local_popups
# def test_memory_leaking(qtbot, make_napari_plot_viewer):
#     data = np.zeros((5, 20, 20, 20), dtype=int)
#     data[1, 0:10, 0:10, 0:10] = 1
#     viewer = make_napari_plot_viewer()
#     image = weakref.ref(viewer.add_image(data))
#     del viewer.layers[0]
#     qtbot.wait(100)
#     gc.collect()
#     gc.collect()
#     assert image() is None
#
#
# @skip_local_popups
# def test_leaks_image(qtbot, make_napari_plot_viewer):
#     viewer = make_napari_plot_viewer(show=True)
#     lr = weakref.ref(viewer.add_image(np.random.rand(10, 10)))
#     dr = weakref.ref(lr().data)
#
#     viewer.layers.clear()
#     qtbot.wait(100)
#     gc.collect()
#     assert not gc.collect()
#     assert not lr()
#     assert not dr()


def test_remove_image(make_napari_plot_viewer):
    viewer = make_napari_plot_viewer()
    viewer.add_image(np.random.rand(10, 10))
    del viewer.layers[0]
    viewer.add_image(np.random.rand(10, 10))


def test_injection_uses_focused_embedded_qt_viewer(qtbot, qapp):
    host = QWidget()
    layout = QVBoxLayout(host)
    viewer1 = ViewerModel(title="viewer-1")
    viewer2 = ViewerModel(title="viewer-2")
    qt_viewer1 = QtViewer(viewer1, parent=host)
    qt_viewer2 = QtViewer(viewer2, parent=host)
    layout.addWidget(qt_viewer1)
    layout.addWidget(qt_viewer2)
    qtbot.addWidget(host)
    host.show()

    assert QtViewer.current() is qt_viewer2

    qt_viewer1.setFocus()
    qapp.processEvents()
    assert _provide_qt_viewer() is qt_viewer1
    assert _provide_viewer(public_proxy=False) is viewer1

    qt_viewer2._enter_canvas()
    qapp.processEvents()
    assert _provide_qt_viewer() is qt_viewer2
    assert _provide_viewer(public_proxy=False) is viewer2
