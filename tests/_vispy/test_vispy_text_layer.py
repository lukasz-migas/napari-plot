"""Tests for the VisPy Text layer adapter."""

from __future__ import annotations

import numpy as np
from napari._vispy.utils.qt_font import FontInfo
from vispy.scene.visuals import Text as VispyTextVisual

from napari_plot._vispy.layers.text import VispyTextLayer
from napari_plot.layers import Text


def _make_visual(monkeypatch, layer: Text) -> VispyTextLayer:
    """Construct a layer adapter without requesting a platform GL context."""
    monkeypatch.setattr(
        "napari._vispy.layers.base.get_max_texture_sizes",
        lambda: (2048, 2048),
    )
    return VispyTextLayer(layer, font_info=FontInfo())


def test_vispy_text_uses_single_visual_and_updates(monkeypatch) -> None:
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
    visual = _make_visual(monkeypatch, layer)

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

    layer.scale_factor = 0.25
    assert visual.node.font_size == 12
    layer.scale_factor = 0.5
    assert visual.node.font_size == 6

    layer.scaling = False
    assert visual.node.font_size == 12
    visual.close()


def test_vispy_text_empty_layer(monkeypatch) -> None:
    """An empty layer uses one transparent dummy label."""
    visual = _make_visual(monkeypatch, Text())

    assert isinstance(visual, VispyTextLayer)
    assert isinstance(visual.node, VispyTextVisual)
    assert visual.node.text == [""]
    np.testing.assert_array_equal(visual.node.color.rgba, [[0, 0, 0, 0]])
    visual.close()
