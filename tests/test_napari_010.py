"""Regression coverage for the napari 0.10 integration."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest
from napari._qt.layer_controls.dynamic.qt_dynamic_layer_controls import QtDynamicLayerControls
from napari.layers.base._base_constants import Blending
from napari.settings import get_settings
from napari.utils import _register
from napari.utils._proxies import ReadOnlyWrapper
from napari.utils.interactions import mouse_move_callbacks, mouse_press_callbacks, mouse_release_callbacks
from napari.utils.key_bindings import KeymapHandler, coerce_keybinding
from npe2 import PluginManifest
from pytestqt.qtbot import QtBot
from vispy.util.keys import Key

from napari_plot._plot_widget import NapariPlotWidget
from napari_plot._qt.component_controls.qt_legend_controls import QtLegendControls
from napari_plot._qt.layer_controls.qt_layer_controls_container import (
    QtLayerControlsContainer,
    QtSharedLayerControls,
)
from napari_plot.components.dragtool import DragMode
from napari_plot.components.viewer_model import ViewerModel
from napari_plot.layers import Scatter, Text


def test_viewer_model_aliases() -> None:
    """Legacy attributes and the new namespaces share model instances."""
    viewer = ViewerModel()
    assert viewer.camera is viewer.scene.camera
    assert viewer.text_overlay is viewer.canvas.overlays.text
    assert viewer.legend is viewer.canvas.overlays.legend
    assert viewer.grid_lines is viewer.canvas.overlays.grid_lines
    viewer._canvas_size = (300, 500)
    assert viewer.canvas.size == (300, 500)
    viewer.canvas.size = (200, 400)
    assert viewer._canvas_size == (200, 400)
    assert _register.create_func.__module__ == "napari.utils._register"


def test_metadata_labels_preserve_user_overrides() -> None:
    """Inherited labels update until the corresponding plot label is edited."""
    viewer = ViewerModel()
    layer = viewer.add_image(np.zeros((2, 3)), axis_labels=("height", "width"))
    assert viewer.dims.axis_labels == ("height", "width")
    assert (viewer.axis.x_label, viewer.axis.y_label) == ("width", "height")
    viewer.axis.x_label = "Time (s)"
    layer.axis_labels = ("amplitude", "time")
    assert viewer.dims.axis_labels == ("amplitude", "time")
    assert (viewer.axis.x_label, viewer.axis.y_label) == ("Time (s)", "amplitude")
    viewer.layers.remove(layer)
    assert viewer.axis.x_label == "Time (s)"
    assert viewer.axis.y_label == "Y-label"


def test_first_layer_fits_without_overwriting_manual_ranges() -> None:
    """Initial extent invalidation fits data and preserves later user navigation."""
    viewer = ViewerModel()
    layer = viewer.plot([1, 2, 3], [1, 4, 2])
    assert viewer.camera.rect == (1, 3, 1, 4)
    viewer.camera.set_rect(1.5, 2.5, 2, 3)
    layer.data = np.array([[1, 1], [2, 5], [4, 2]])
    assert viewer.camera.rect == (1.5, 2.5, 2, 3)


def test_legend_controls_disconnect_psygnal_overlays(qtbot: QtBot) -> None:
    """Closing the popup disconnects the new overlay signal group safely."""
    viewer = ViewerModel()
    controls = QtLegendControls(viewer)
    qtbot.addWidget(controls)
    controls.close()
    viewer.legend.font_size = 21


def test_embedded_axis_domains_follow_layout(make_napari_viewer: Callable, qtbot: QtBot) -> None:
    """Docking and resizing keep tick labels aligned with the plotted data."""
    host = make_napari_viewer(strict_qt=False)
    widget = NapariPlotWidget(host)
    qtbot.addWidget(widget)
    widget.viewer_plot.plot([1, 2, 3], [1, 4, 2])
    host.window.add_dock_widget(widget, area="bottom")
    host.window._qt_window.resize(800, 600)
    host.show()
    canvas = widget.qt_viewer.canvas
    qtbot.waitUntil(lambda: np.allclose(canvas.x_axis.node.axis.domain, (1, 3), atol=1e-5))
    qtbot.waitUntil(lambda: np.allclose(canvas.y_axis.node.axis.domain, (1, 4), atol=1e-5))


@pytest.mark.parametrize("dynamic", [False, True])
def test_custom_and_shared_controls(dynamic: bool, qtbot: QtBot) -> None:
    """Experimental controls keep custom panels and support mixed selections."""
    settings = get_settings()
    with patch.object(settings.experimental, "dynamic_layer_controls", dynamic):
        viewer = ViewerModel()
        line = viewer.add_line([[0, 0], [1, 1]])
        container = QtLayerControlsContainer(viewer)
        qtbot.addWidget(container)
        assert container.currentWidget() is container.widgets[line]
        image = viewer.add_image(np.zeros((2, 2)))
        viewer.layers.selection.select_only(image)
        if dynamic:
            assert isinstance(container.panel, QtDynamicLayerControls)
        else:
            assert container.currentWidget() is container.widgets[image]
        viewer.layers.selection.update([line, image])
        assert isinstance(container.panel, QtSharedLayerControls)
        container.panel.controls.opacity_slider.setValue(0.35)
        assert line.opacity == pytest.approx(0.35)
        assert image.opacity == pytest.approx(0.35)
        container.panel.controls.blend_combobox.setCurrentEnum(Blending.ADDITIVE)
        assert line.blending == image.blending == "additive"
        viewer.layers.remove(image)
        viewer.layers.selection.select_only(line)
        assert container.currentWidget() is container.widgets[line]
        viewer.layers.remove(line)
        assert not container.widgets


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [({}, "none"), ({"out_of_slice_display": False}, "all"), ({"n_dimensional": True}, "rescale_linear")],
)
def test_scatter_projection_arguments(kwargs: dict[str, bool], expected: str) -> None:
    """Legacy arguments are translated only when explicitly supplied."""
    layer = Scatter([[1, 2]], projection_mode="none", **kwargs)
    assert layer.projection_mode == expected


def test_fonts_inherit_settings() -> None:
    """Unspecified text and legend sizes follow appearance settings."""
    viewer = ViewerModel()
    text = Text([[0, 0]], "label")
    explicit = Text([[0, 0]], "label", size=23)
    with patch.object(get_settings().appearance, "font_size", 18):
        assert text.size is None
        assert text.effective_size == 18
        assert explicit.effective_size == 23
        assert viewer.legend.font_size is None
        assert viewer.legend.effective_font_size == 18
        viewer.legend.font_size = 25
        assert viewer.legend.effective_font_size == 25


def test_widget_docking_defaults() -> None:
    """Both plugin contributions default to a tabified bottom dock."""
    manifest = PluginManifest.from_file(Path(__file__).parents[1] / "napari_plot" / "napari.yaml")
    for widget in manifest.contributions.widgets:
        assert widget.default_dock_area == "bottom"
        assert widget.tabify


@pytest.mark.parametrize(
    ("method", "data"),
    [
        ("add_line", [[1, 2], [3, 4]]),
        ("add_scatter", [[1, 2], [3, 4]]),
        ("add_text", [[1, 2], [3, 4]]),
        ("add_bar", [1, 2]),
        ("add_centroids", [[1, 2], [3, 4]]),
        ("add_multi_line", (np.array([1, 2]), np.array([3, 4]))),
        ("add_region", [[1, 2]]),
        ("add_inf_line", [1, 2]),
    ],
)
def test_layer_visual_lifecycle(
    method: str, data: list | tuple, make_napari_plot_viewer: Callable, qtbot: QtBot
) -> None:
    """Every custom layer can update, render, and dispose its visual."""
    viewer = make_napari_plot_viewer()
    canvas = viewer.window._qt_viewer.canvas
    layer = getattr(viewer, method)(data)
    layer.refresh()
    canvas.on_draw(None)
    assert layer in canvas.layer_to_visual
    if isinstance(layer, Scatter):
        layer.data = np.empty((0, 2))
        canvas.on_draw(None)
    viewer.layers.remove(layer)
    assert layer not in canvas.layer_to_visual


def test_canvas_background_and_fonts(make_napari_plot_viewer: Callable) -> None:
    """Canvas model changes reach the renderer without replacing the camera."""
    viewer = make_napari_plot_viewer()
    canvas = viewer.window._qt_viewer.canvas
    text = viewer.add_text([[1, 2]], "inherited")
    explicit = viewer.add_text([[2, 3]], "explicit", size=22)
    viewer.legend.set_entries([{"label": "sample", "color": "red"}])
    viewer.canvas.background_color_override = "red"
    viewer.theme = "light"
    np.testing.assert_allclose(canvas._scene_canvas.bgcolor.rgba, [1, 0, 0, 1])
    viewer.canvas.background_color_override = None
    np.testing.assert_allclose(canvas._scene_canvas.bgcolor.rgba, viewer.canvas.background_color)
    with patch.object(get_settings().appearance, "font_size", 19):
        assert canvas.layer_to_visual[text].node.font_size == 19
        assert canvas.layer_to_visual[explicit].node.font_size == 22
        assert canvas._overlay_to_visual[viewer.legend]._text.font_size == 19


@pytest.mark.parametrize("key", ["V", "G", "L"])
def test_toggle_shortcuts_run_once_per_press(key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Held toggle shortcuts do not oscillate with OS key repeat."""
    viewer = ViewerModel()
    layer = viewer.add_scatter([[1, 2]])
    handler = KeymapHandler()
    handler.keymap_providers = [viewer]
    binding = coerce_keybinding(key if key == "V" else f"Control-{key}")
    monkeypatch.setattr("napari.utils.key_bindings._vispy2appmodel", lambda _event: binding)
    modifiers = [] if key == "V" else ["Control"]
    event = SimpleNamespace(
        key=Key(key), modifiers=modifiers, native=SimpleNamespace(isAutoRepeat=lambda: False), handled=False
    )
    handler.on_key_press(event)
    assert event.handled
    state = (layer.visible, layer.editable, viewer.grid_lines.visible)
    assert state != (True, True, False)
    event.native = SimpleNamespace(isAutoRepeat=lambda: True)
    handler.on_key_press(event)
    assert (layer.visible, layer.editable, viewer.grid_lines.visible) == state
    handler.on_key_release(event)
    event.native = SimpleNamespace(isAutoRepeat=lambda: False)
    handler.on_key_press(event)
    assert layer.visible
    assert layer.editable
    assert not viewer.grid_lines.visible
    handler.on_key_release(event)


@pytest.mark.parametrize("mode", [DragMode.BOX, DragMode.LASSO, DragMode.POLYGON, DragMode.BOX_SELECT])
def test_drag_completion_and_cancellation(mode: DragMode) -> None:
    """The current callback machinery completes gestures and cancels mode changes."""
    viewer = ViewerModel()
    viewer.drag_tool.active = mode

    def event(kind: str, position: tuple[int, int], button: int = 1) -> ReadOnlyWrapper:
        return ReadOnlyWrapper(
            SimpleNamespace(
                type=kind,
                pos=np.array(position),
                position=position,
                button=button,
                modifiers=[],
                is_dragging=kind == "mouse_move",
            )
        )

    mouse_press_callbacks(viewer, event("mouse_press", (0, 0)))
    mouse_move_callbacks(viewer, event("mouse_move", (20, 30)))
    mouse_release_callbacks(viewer, event("mouse_release", (20, 30)))
    assert not viewer._mouse_drag_gen
    assert not viewer._persisted_mouse_event

    mouse_press_callbacks(viewer, event("mouse_press", (0, 0)))
    previous_tool = viewer.drag_tool.tool
    viewer.drag_tool.active = DragMode.NONE
    assert not viewer._mouse_drag_gen
    assert not viewer._persisted_mouse_event
    assert not previous_tool.visible
