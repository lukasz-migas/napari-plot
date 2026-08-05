"""Check QtViewer"""

import weakref
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from qtpy.QtCore import QEvent
from qtpy.QtGui import QFocusEvent, QGuiApplication
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
    emitter = viewer._layer_slicer.events.ready
    callback, _ = emitter._normalize_cb(view._on_slice_ready)
    assert callback in emitter.callbacks

    assert len(viewer.layers) == 0
    assert view.layers.model().rowCount() == 0


def test_on_slice_ready_uses_layer_slicing_state():
    """Completed async slices are applied through napari's slicing state."""
    layer = Mock()
    response = SimpleNamespace(request_id=7)
    event = SimpleNamespace(value={weakref.ref(layer): response})

    QtViewer._on_slice_ready.__wrapped__(object(), event)

    layer._slicing_state._update_slice_response.assert_called_once_with(response)
    layer._slicing_state._update_loaded_slice_id.assert_called_once_with(7)
    layer.events.set_data.assert_called_once_with()
    layer._refresh_sync.assert_called_once_with(
        data_displayed=False,
        thumbnail=True,
        highlight=True,
        extent=True,
    )


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


@skip_on_win_ci
def test_toolbar_screenshot_copies_image(make_napari_plot_viewer):
    """The toolbar screenshot action calls correctly bound napari methods."""
    viewer = make_napari_plot_viewer()
    qt_viewer = viewer.window._qt_viewer

    image = qt_viewer._screenshot(flash=False)
    assert not image.isNull()
    qt_viewer.viewerToolbar.tools_clip_btn.click()
    assert not QGuiApplication.clipboard().image().isNull()


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


def test_injection_uses_focused_embedded_qt_viewer(qtbot, monkeypatch):
    monkeypatch.setattr("napari_plot._vispy.canvas.get_max_texture_sizes", lambda: (2048, 2048))
    host = QWidget()
    layout = QVBoxLayout(host)
    viewer1 = ViewerModel(title="viewer-1")
    viewer2 = ViewerModel(title="viewer-2")
    qt_viewer1 = QtViewer(viewer1, parent=host)
    qt_viewer2 = QtViewer(viewer2, parent=host)
    layout.addWidget(qt_viewer1)
    layout.addWidget(qt_viewer2)
    qtbot.addWidget(host)
    assert QtViewer.current() is qt_viewer2

    qt_viewer1.focusInEvent(QFocusEvent(QEvent.Type.FocusIn))
    assert _provide_qt_viewer() is qt_viewer1
    assert _provide_viewer(public_proxy=False) is viewer1

    qt_viewer2._enter_canvas()
    assert _provide_qt_viewer() is qt_viewer2
    assert _provide_viewer(public_proxy=False) is viewer2
