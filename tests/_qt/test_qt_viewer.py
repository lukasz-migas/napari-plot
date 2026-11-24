"""Check QtViewer"""

import weakref
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from napari.components._viewer_constants import CanvasPosition
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


def test_text_overlay_background_tracks_text_geometry(
    make_napari_plot_viewer,
    qtbot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The text background should follow the full label in the plot viewport."""
    monkeypatch.setattr("napari_plot._vispy.canvas.get_max_texture_sizes", lambda: (2048, 2048))
    viewer = make_napari_plot_viewer(show=True)
    canvas = viewer.window._qt_viewer.canvas
    # Give the plot room for the label independently of the dock and window sizes.
    canvas.native.setFixedSize(600, 400)
    viewer.add_line([[0, 0], [1, 1]])
    overlay = viewer.text_overlay
    visual = canvas._overlay_to_visual[overlay][0]

    overlay.position = CanvasPosition.TOP_LEFT
    overlay.font_size = 12
    overlay.text = "label"
    overlay.visible = True
    qtbot.waitUntil(lambda: visual.x_size > 0 and visual.y_size > 0)

    assert visual.box.parent is visual.node.parent
    assert visual.box.width > visual.x_size
    assert visual.box.height > visual.y_size
    top_left = np.asarray(visual.node.transform.translate[:2], dtype=float)
    assert np.all(top_left >= 0)

    short_width = visual.box.width
    overlay.text = "longer overlay label"
    qtbot.waitUntil(lambda: visual.box.width > short_width)
    qtbot.waitUntil(lambda: visual.node.parent.size[0] > visual.box.width + 40)

    overlay.position = CanvasPosition.BOTTOM_RIGHT
    available_size = np.asarray(visual.node.parent.size, dtype=float)
    bottom_right = np.asarray(visual.node.transform.translate[:2], dtype=float)
    assert np.all(bottom_right >= 0)
    assert bottom_right[0] + visual.x_size <= available_size[0]
    assert bottom_right[1] + visual.y_size <= available_size[1]

    default_size = visual.box.width, visual.box.height
    visual.box_padding = (20, 12)
    assert visual.box.width == pytest.approx(visual.x_size + 40)
    assert visual.box.height == pytest.approx(visual.y_size + 24)
    # the canvas re-tiles on the next draw after the visual reports its new margin
    qtbot.waitUntil(
        lambda: np.all(
            np.asarray(visual.node.transform.translate[:2]) + (visual.x_size + 20, visual.y_size + 12)
            <= available_size + 1e-6
        )
    )

    visual.box_padding = None
    assert (visual.box.width, visual.box.height) == pytest.approx(default_size)
    visual.box_padding = (0, 0)
    assert (visual.box.width, visual.box.height) == pytest.approx((visual.x_size, visual.y_size))
    overlay.text = ""
    assert visual.box.parent is None
    overlay.box = False
    assert visual.box.parent is None


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


def test_napari_layer_control_actions_use_plot_layer(make_napari_plot_viewer):
    """napari's own layer-control actions (e.g. Points add) find the active napari-plot layer."""
    from napari.layers import Points
    from napari.utils.action_manager import action_manager

    viewer = make_napari_plot_viewer()
    layer = viewer.add_layer(Points(np.zeros((1, 2))))
    action_manager.trigger("napari:activate_points_add_mode")
    assert layer.mode == "add"
