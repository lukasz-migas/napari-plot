"""Tests for text anchored to the plot area."""

from __future__ import annotations

from napari_plot.components.viewer_model import ViewerModel


def test_add_text_overlay_adds_replaces_and_resets() -> None:
    """Text overlays are kept by name, replaced when added again and removed by `reset_plot`."""
    viewer = ViewerModel()

    first = viewer.add_text_overlay("R² = 0.99", position="top_left", name="stats", font_size=9)
    viewer.add_text_overlay("note", position="bottom_right")
    assert first.visible
    assert first.position == "top_left"
    assert first.font_size == 9

    second = viewer.add_text_overlay("R² = 0.98", name="stats")
    assert viewer._overlays["annotation:stats"] is second
    assert len(viewer._text_overlay_names) == 2

    viewer.reset_plot()
    assert not any(str(key).startswith("annotation:") for key in viewer._overlays)
    assert viewer.text_overlay is not None


def test_text_overlays_get_and_lose_visuals(make_napari_plot_viewer) -> None:
    """The canvas creates a visual for added text overlays and closes it when they are removed."""
    viewer = make_napari_plot_viewer()
    canvas = viewer.window._qt_viewer.canvas

    overlay = viewer.add_text_overlay("hello", position="top_right")
    assert overlay in canvas._overlay_to_visual
    assert canvas._overlay_to_visual[overlay][0].node.text == "hello"

    viewer.remove_text_overlays()
    assert overlay not in canvas._overlay_to_visual
