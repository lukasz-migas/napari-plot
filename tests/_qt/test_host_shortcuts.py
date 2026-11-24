"""Embedding napari-plot must leave the host napari keymap untouched."""

import napari.utils.action_manager as napari_action_manager
from napari.settings import get_settings
from napari.utils.shortcuts import default_shortcuts

from napari_plot.utils.action_manager import Action, action_manager


def test_plot_viewer_keeps_napari_shortcuts(make_napari_plot_viewer) -> None:
    """Creating a plot viewer neither clears napari's defaults nor its saved shortcuts."""
    import napari_plot._qt.qt_viewer  # noqa: F401

    before = dict(get_settings().shortcuts.shortcuts)
    make_napari_plot_viewer()

    assert default_shortcuts
    assert "napari:toggle_console_visibility" in default_shortcuts
    assert get_settings().shortcuts.shortcuts == before


def test_plot_actions_do_not_patch_napari_action() -> None:
    """napari-plot actions use their own Action class while napari keeps its own."""
    assert napari_action_manager.Action is not Action
    assert all(isinstance(action, Action) for action in action_manager._actions.values())
    assert action_manager is not napari_action_manager.action_manager
