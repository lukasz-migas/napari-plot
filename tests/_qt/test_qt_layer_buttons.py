"""Tests for layer creation controls."""

import numpy as np
import pytest

from napari_plot._qt.qt_layer_buttons import QtLayerButtons, _add_empty_layer, create_add_layer_menu
from napari_plot.components.viewer_model import ViewerModel


def test_add_layer_menu_lists_all_supported_layers(qtbot) -> None:
    """The compact menu exposes all built-in and custom creation actions."""
    viewer = ViewerModel()
    buttons = QtLayerButtons(viewer)
    qtbot.addWidget(buttons)
    menu = create_add_layer_menu(buttons, viewer)
    qtbot.addWidget(menu)

    assert [action.text() for action in menu.actions()] == [
        "Add Line",
        "Add Bar",
        "Add Scatter",
        "Add MultiLine",
        "Add Centroids",
        "Add Text",
        "Add Region",
        "Add InfLine",
        "Add Points",
        "Add Shapes",
    ]


@pytest.mark.parametrize(
    ("layer_name", "expected_type"),
    [
        ("Line", "Line"),
        ("Bar", "Bar"),
        ("Scatter", "Scatter"),
        ("MultiLine", "MultiLine"),
        ("Centroids", "Centroids"),
        ("Text", "Text"),
        ("Region", "Region"),
        ("InfLine", "InfLine"),
        ("Points", "Points"),
        ("Shapes", "Shapes"),
    ],
)
def test_add_empty_layer(layer_name: str, expected_type: str) -> None:
    """Every layer action creates a valid empty layer."""
    viewer = ViewerModel()

    layer = _add_empty_layer(viewer, layer_name)

    assert type(layer).__name__ == expected_type
    assert viewer.layers[-1] is layer


@pytest.mark.parametrize("layer_name", ["Bar", "Centroids", "MultiLine"])
def test_add_empty_layer_is_safe_in_qt_viewer(make_napari_plot_viewer, layer_name: str) -> None:
    """Empty custom layers initialize controls and visuals, then accept data."""
    viewer = make_napari_plot_viewer()
    qt_viewer = viewer.window._qt_viewer

    layer = _add_empty_layer(viewer, layer_name)

    assert layer in qt_viewer.controls.widgets
    assert layer in qt_viewer.canvas.layer_to_visual

    controls = qt_viewer.controls.widgets[layer]
    if layer_name == "Bar":
        visual = qt_viewer.canvas.layer_to_visual[layer]
        assert not visual.node.mesh.visible
        layer.data = [[0, 1]]
        assert visual.node.mesh.visible
    elif layer_name == "Centroids":
        assert not controls.selection_spin.isEnabled()
        layer.data = [[0, 0, 1]]
        assert controls.selection_spin.isEnabled()
    else:
        assert not controls.selection_spin.isEnabled()
        layer.data = (np.asarray([0, 1]), np.asarray([1, 2]))
        assert controls.selection_spin.isEnabled()
