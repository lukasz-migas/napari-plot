"""Tests for render data, visibility, and uploads."""

from unittest.mock import patch

import numpy as np
import pytest
from napari._vispy.utils.qt_font import FontInfo

from napari_plot._vispy.layers.rectangles import VispyRectanglesLayer
from napari_plot._vispy.visuals.rectangles import RectangleOutlineVisual
from napari_plot.layers import Rectangles


def test_vispy_rectangles_independent_visibility_and_alignment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("napari._vispy.layers.base.get_max_texture_sizes", lambda: (2048, 2048))
    layer = Rectangles([[10, 200], [30, 400]], [8, 12], 4, text=["", "Peak"], text_offset=(2, 0.5))
    adapter = VispyRectanglesLayer(layer, font_info=FontInfo())
    outlines, markers, text = adapter.node.outlines, adapter.node.markers, adapter.node.text
    assert outlines.visible
    assert text.visible
    assert not markers.visible
    np.testing.assert_array_equal(text.pos[:, :2], [[32, 400.5]])

    layer.show_rectangles = False
    layer.show_text = False
    layer.show_markers = True
    assert markers.visible
    assert not outlines.visible
    assert not text.visible
    np.testing.assert_array_equal(markers._data["a_position"][:, :2], layer.centers)
    layer.set_data([[5, 9], [15, 25]], 2, 7)
    layer.show_text = True
    np.testing.assert_array_equal(markers._data["a_position"][:, :2], layer.centers)
    np.testing.assert_array_equal(text.pos[:, :2], [[17, 25.5]])
    layer.text = ["", ""]
    assert not text.visible
    layer.data = None
    assert not any(node.visible for node in (outlines, markers, text))


def test_vispy_rectangles_uploads_only_changed_enabled_components(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("napari._vispy.layers.base.get_max_texture_sizes", lambda: (2048, 2048))
    layer = Rectangles([[0, 0]], 2, 4, show_rectangles=False)
    adapter = VispyRectanglesLayer(layer, font_info=FontInfo())
    outlines = adapter.node.outlines
    with (
        patch.object(RectangleOutlineVisual, "set_geometry", wraps=outlines.set_geometry) as upload_geometry,
        patch.object(RectangleOutlineVisual, "set_color", wraps=outlines.set_color) as upload_color,
    ):
        layer.set_data([[2, 3], [4, 5]], 2, 3)
        layer.outline_color = ["red", "green"]
        upload_geometry.assert_not_called()
        upload_color.assert_not_called()
        layer.show_rectangles = True
        upload_geometry.assert_called_once()
        upload_color.assert_called_once()
        upload_geometry.reset_mock()
        upload_color.reset_mock()

        layer.outline_width = 4
        layer.refresh()
        layer.show_rectangles = False
        layer.show_rectangles = True
        upload_geometry.assert_not_called()
        upload_color.assert_not_called()
        layer.outline_color = "blue"
        upload_geometry.assert_not_called()
        upload_color.assert_called_once()

        layer.set_data([[4, 5], [8, 10]], 5, 10)
        upload_geometry.assert_called_once()
