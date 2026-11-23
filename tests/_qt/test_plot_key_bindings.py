"""Test registered shortcuts through napari's key dispatcher."""

import sys
from types import SimpleNamespace

import pytest
from napari.utils.key_bindings import KeymapHandler
from vispy.util.keys import Key

from napari_plot.components.viewer_model import ViewerModel

CONTROL = "Meta" if sys.platform == "darwin" else "Control"


def _key(name: str, *modifiers: str) -> SimpleNamespace:
    return SimpleNamespace(key=Key(name), modifiers=modifiers, native=None, handled=False)


def test_plot_key_bindings_select_reset_and_remove_layers() -> None:
    """Canvas key events reach viewer commands with their registered modifiers."""
    viewer = ViewerModel()
    first = viewer.add_line([[0, 0], [2, 2]])
    second = viewer.add_line([[0, 2], [2, 0]])
    handler = KeymapHandler()
    handler.keymap_providers = [viewer]

    event = _key("Down")
    handler.on_key_press(event)
    assert event.handled
    assert viewer.layers.selection.active is first

    expected = viewer.camera.rect
    viewer.camera.rect = (0.5, 1, 0.5, 1)
    event = _key("R", CONTROL)
    handler.on_key_press(event)
    assert event.handled
    assert viewer.camera.rect == pytest.approx(expected)

    event = _key("A", CONTROL)
    handler.on_key_press(event)
    assert event.handled
    assert set(viewer.layers.selection) == {first, second}

    event = _key("Delete", CONTROL)
    handler.on_key_press(event)
    assert event.handled
    assert not viewer.layers


def test_region_key_release_restores_editing_mode() -> None:
    """The active Region's Space binding pans temporarily, then restores editing."""
    viewer = ViewerModel()
    layer = viewer.add_region([[0, 1]])
    handler = KeymapHandler()
    handler.keymap_providers = [layer, viewer]
    layer.mode = "add"

    event = _key("Space")
    handler.on_key_press(event)
    assert event.handled
    assert layer.mode == "pan_zoom"
    handler.on_key_release(event)
    assert layer.mode == "add"
