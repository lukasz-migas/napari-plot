"""Tests for the VisPy Text layer adapter."""

from __future__ import annotations

import numpy as np
import pytest
from napari._vispy.utils.qt_font import FontInfo
from qtpy.QtWidgets import QApplication
from vispy.visuals import TextVisual as VispyTextVisual

from napari_plot._vispy.layers.text import VispyTextLayer
from napari_plot.layers import Text


def _make_visual(
    monkeypatch: pytest.MonkeyPatch,
    layer: Text,
    qapp: QApplication,
) -> VispyTextLayer:
    """Construct a layer adapter without requesting a platform GL context."""
    assert QApplication.instance() is qapp
    monkeypatch.setattr(
        "napari._vispy.layers.base.get_max_texture_sizes",
        lambda: (2048, 2048),
    )
    return VispyTextLayer(layer, font_info=FontInfo())


def test_vispy_text_uses_single_visual_and_updates(
    monkeypatch: pytest.MonkeyPatch,
    qapp: QApplication,
) -> None:
    """All labels and vectorized styles are assigned to one native visual."""
    layer = Text(
        [[1, 2], [3, 4], [5, 6]],
        ["a", "b", "c"],
        size=20,
        color=["red", "blue", "green"],
        alignment="left",
        rotation=[0, 10, 20],
        offset=[[1, 0], [0, 1], [1, 1]],
        font_face="Arial",
        bold=True,
        italic=True,
    )
    visual = _make_visual(monkeypatch, layer, qapp)

    assert isinstance(visual, VispyTextLayer)
    assert isinstance(visual.node, VispyTextVisual)
    assert visual.node.text == ["a", "b", "c"]
    np.testing.assert_array_equal(visual.node.pos, [[2, 2, 0], [3, 5, 0], [6, 7, 0]])
    assert visual.node.font_size == 20
    assert visual.node.anchors == ("left", "center")
    assert visual.node.face == "Arial"
    assert visual.node.bold is True
    assert visual.node.italic is True
    np.testing.assert_array_equal(visual.node.rotation, [0, 10, 20])
    np.testing.assert_array_equal(
        visual.node.color.rgba[:2],
        [[1, 0, 0, 1], [0, 0, 1, 1]],
    )

    layer.size = 12
    layer.alignment = "center"
    assert visual.node.font_size == 12
    assert visual.node.anchors == ("center", "center")
    visual.close()


def test_vispy_text_empty_layer(
    monkeypatch: pytest.MonkeyPatch,
    qapp: QApplication,
) -> None:
    """An empty layer uses one transparent dummy label."""
    visual = _make_visual(monkeypatch, Text(), qapp)

    assert isinstance(visual, VispyTextLayer)
    assert isinstance(visual.node, VispyTextVisual)
    assert visual.node.text == [""]
    np.testing.assert_array_equal(visual.node.color.rgba, [[0, 0, 0, 0]])
    visual.close()


def test_vispy_text_passes_pixel_offsets(
    monkeypatch: pytest.MonkeyPatch,
    qapp: QApplication,
) -> None:
    """Pixel offsets reach the native visual and follow later changes."""
    layer = Text([[1, 2], [3, 4]], ["a", "b"], pixel_offset=[[4, 4], [-4, 8]])
    visual = _make_visual(monkeypatch, layer, qapp)

    np.testing.assert_allclose(visual.node.pixel_offset, [[4, 4], [-4, 8]])
    layer.pixel_offset = (2, 3)
    np.testing.assert_allclose(visual.node.pixel_offset, [[2, 3], [2, 3]])


def test_pixel_offset_shader_adds_screen_shift() -> None:
    """The text vertex shader gets a per-glyph pixel shift added to the glyph offset."""
    from napari_plot._vispy.visuals.text import PixelOffsetTextVisual

    vertex = PixelOffsetTextVisual._shaders["vertex"]
    assert "attribute vec2 a_px_offset;" in vertex
    assert vertex.index("offset.xy += a_px_offset * u_px_scale;") < vertex.index("gl_Position =")
