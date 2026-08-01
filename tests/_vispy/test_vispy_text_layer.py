"""Tests for the VisPy Text layer adapter."""

from __future__ import annotations

import numpy as np
from napari._vispy.utils.qt_font import FontInfo

from napari_plot._vispy.layers.text import VispyTextLayer
from napari_plot._vispy.utils.visual import layer_to_visual
from napari_plot.layers import Text


def _make_visual(monkeypatch, layer: Text) -> VispyTextLayer:
    """Construct a layer adapter without requesting a platform GL context."""
    monkeypatch.setattr(
        "napari._vispy.layers.base.get_max_texture_sizes",
        lambda: (2048, 2048),
    )
    return VispyTextLayer(layer, font_info=FontInfo())


def test_vispy_text_groups_and_updates(monkeypatch) -> None:
    """Labels are grouped by size and alignment and regroup after updates."""
    layer = Text(
        [[1, 2], [3, 4], [5, 6]],
        ["a", "b", "c"],
        size=[10, 10, 20],
        color=["red", "blue", "green"],
        alignment=["left", "left", "right"],
        rotation=[0, 10, 20],
        offset=[[1, 0], [0, 1], [1, 1]],
        font_face="Arial",
        bold=True,
        italic=True,
    )
    visual = _make_visual(monkeypatch, layer)

    assert isinstance(visual, VispyTextLayer)
    assert len(visual.node._subvisuals) == 2
    first, second = visual.node._subvisuals
    assert first.text == ["a", "b"]
    np.testing.assert_array_equal(first.pos, [[2, 2, 0], [3, 5, 0]])
    assert first.font_size == 10
    assert first.anchors == ("left", "center")
    assert first.face == "Arial"
    assert first.bold is True
    assert first.italic is True
    np.testing.assert_array_equal(first.rotation, [0, 10])
    np.testing.assert_array_equal(first.color.rgba, [[1, 0, 0, 1], [0, 0, 1, 1]])
    assert second.text == ["c"]
    assert second.font_size == 20

    layer.scale_factor = 2
    assert first.font_size == 5
    assert second.font_size == 10

    layer.scaling = False
    assert first.font_size == 10
    assert second.font_size == 20

    layer.size = 12
    layer.alignment = "center"

    assert len(visual.node._subvisuals) == 1
    assert visual.node._subvisuals[0].text == ["a", "b", "c"]
    assert visual.node._subvisuals[0].font_size == 12
    visual.close()


def test_vispy_text_empty_layer(monkeypatch) -> None:
    """An empty text layer creates no native text batches."""
    visual = _make_visual(monkeypatch, Text())

    assert isinstance(visual, VispyTextLayer)
    assert visual.node._subvisuals == []
    visual.close()


def test_vispy_text_layer_is_registered() -> None:
    """The canvas visual factory knows how to render Text layers."""
    assert layer_to_visual[Text] is VispyTextLayer
