"""Tests for the Bar VisPy adapter."""

import pytest
from napari._vispy.utils.qt_font import FontInfo

from napari_plot._vispy.layers.bar import VispyBarLayer
from napari_plot.layers import Bar


def test_vispy_bar_layer_updates_geometry(monkeypatch: pytest.MonkeyPatch) -> None:
    """The adapter creates fill triangles and border segments."""
    # Avoid querying an OpenGL context; geometry updates do not require one.
    monkeypatch.setattr("napari._vispy.layers.base.get_max_texture_sizes", lambda: (2048, 2048))
    layer = Bar([[0, 1], [1, 2]], fill_color=["red", "blue"])
    visual = VispyBarLayer(layer, font_info=FontInfo())

    assert visual.node.mesh.mesh_data.get_vertices().shape == (8, 2)
    assert visual.node.border.pos.shape == (16, 2)

    layer.data = [[0, 3]]
    assert visual.node.mesh.mesh_data.get_vertices().shape == (4, 2)


def test_vispy_bar_layer_handles_empty_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty bar visual stays hidden until data is assigned."""
    monkeypatch.setattr("napari._vispy.layers.base.get_max_texture_sizes", lambda: (2048, 2048))
    layer = Bar(None)
    visual = VispyBarLayer(layer, font_info=FontInfo())

    assert not visual.node.mesh.visible
    assert not visual.node.border.visible

    layer.data = [[0, 1]]
    assert visual.node.mesh.visible
    assert visual.node.border.visible
    assert visual.node.mesh.mesh_data.get_vertices().shape == (4, 2)
