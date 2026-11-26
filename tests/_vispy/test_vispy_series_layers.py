"""Tests for the Centroids and MultiLine render data adapters."""

import numpy as np
import pytest
from napari._vispy.utils.qt_font import FontInfo

from napari_plot._vispy.layers.centroids import VispyCentroidsLayer
from napari_plot._vispy.layers.multiline import LINE_MAIN, VispyMultiLineLayer
from napari_plot.layers import Centroids, MultiLine


def test_centroids_visual_orientation_and_color(monkeypatch: pytest.MonkeyPatch) -> None:
    """Changing orientation swaps coordinates without losing the segment colors."""
    monkeypatch.setattr("napari._vispy.layers.base.get_max_texture_sizes", lambda: (2048, 2048))
    layer = Centroids([[2, 1, 3], [4, -1, 2]], color=["red", "blue"])
    visual = VispyCentroidsLayer(layer, font_info=FontInfo())
    try:
        np.testing.assert_array_equal(visual.node.pos, [[2, 3], [2, 1], [4, 2], [4, -1]])
        layer.orientation = "horizontal"
        np.testing.assert_array_equal(visual.node.pos, [[3, 2], [1, 2], [2, 4], [-1, 4]])
        layer.update_color(1, np.array([0, 1, 0, 1]))
        np.testing.assert_allclose(visual.node.color[:2], [[1, 0, 0, 1]] * 2)
        np.testing.assert_allclose(visual.node.color[2:], [layer.color[1]] * 2)
        layer.visible = False
        assert not visual.node.visible
    finally:
        visual.close()


def test_multiline_visual_keeps_disconnected_series_when_streaming(monkeypatch: pytest.MonkeyPatch) -> None:
    """A stream update preserves geometry breaks and the colors of individual lines."""
    monkeypatch.setattr("napari._vispy.layers.base.get_max_texture_sizes", lambda: (2048, 2048))
    x = np.arange(3)
    y = [np.array([1, 2, 3]), np.array([-1, -2, -3])]
    layer = MultiLine({"x": x, "ys": y}, color=["red", "blue"])
    visual = VispyMultiLineLayer(layer, font_info=FontInfo())
    try:
        node = visual.node._subvisuals[LINE_MAIN]
        np.testing.assert_array_equal(node._connect, [[0, 1], [1, 2], [3, 4], [4, 5]])
        np.testing.assert_array_equal(node.color, [[1, 0, 0, 1]] * 3 + [[0, 0, 1, 1]] * 3)
        layer.stream({"x": x, "ys": [y[0] + 1, y[1] - 1]})
        np.testing.assert_array_equal(node.pos[:, 1], [2, 3, 4, -2, -3, -4])
        np.testing.assert_array_equal(node._connect, [[0, 1], [1, 2], [3, 4], [4, 5]])
        layer.width = 3
        assert node.width == 3
    finally:
        visual.close()


def test_multiline_visual_follows_line_lengths_when_streaming(monkeypatch: pytest.MonkeyPatch) -> None:
    """Streaming lines of a different length updates the connections and keeps the line colors."""
    monkeypatch.setattr("napari._vispy.layers.base.get_max_texture_sizes", lambda: (2048, 2048))
    layer = MultiLine({"xs": [np.arange(3), np.arange(3)], "ys": [np.ones(3), -np.ones(3)]}, color=["red", "blue"])
    visual = VispyMultiLineLayer(layer, font_info=FontInfo())
    try:
        node = visual.node._subvisuals[LINE_MAIN]
        layer.stream({"xs": [np.arange(2), np.arange(4)], "ys": [np.ones(2), -np.ones(4)]})
        np.testing.assert_array_equal(node._connect, [[0, 1], [2, 3], [3, 4], [4, 5]])
        np.testing.assert_array_equal(node.color, [[1, 0, 0, 1]] * 2 + [[0, 0, 1, 1]] * 4)
    finally:
        visual.close()


def test_areas_visual_redraws_streamed_areas(monkeypatch: pytest.MonkeyPatch) -> None:
    """Streamed areas are drawn without a data event and keep their fill colors."""
    from napari_plot._vispy.layers.areas import VispyAreasLayer
    from napari_plot.layers import Areas

    monkeypatch.setattr("napari._vispy.layers.base.get_max_texture_sizes", lambda: (2048, 2048))
    layer = Areas([[[0, 0, 1], [1, 0, 2]]], fill_color="red")
    visual = VispyAreasLayer(layer, font_info=FontInfo())
    data_events = []
    layer.events.data.connect(data_events.append)
    try:
        layer.stream([[[0, 0, 5], [1, 0, 6], [2, 0, 7]]])
        assert not data_events
        assert layer.data[0].shape == (3, 3)
        np.testing.assert_array_equal(layer.fill_color, [[1, 0, 0, 1]])
        assert visual.node.mesh.mesh_data.get_vertices()[:, 1].max() == 7
    finally:
        visual.close()


def test_areas_visual_keeps_its_shader_when_the_data_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    """New areas or colors only upload buffers; the mesh's color function stays, so its program is not recompiled."""
    from napari_plot._vispy.layers.areas import VispyAreasLayer
    from napari_plot.layers import Areas

    monkeypatch.setattr("napari._vispy.layers.base.get_max_texture_sizes", lambda: (2048, 2048))
    layer = Areas([[[0, 0, 1], [1, 0, 2]]], fill_color="red")
    visual = VispyAreasLayer(layer, font_info=FontInfo())
    mesh = visual.node.mesh
    try:
        mesh._update_data()
        color_function = mesh.shared_program.vert["color_transform"]
        layer.stream([[[0, 0, 5], [1, 0, 6], [2, 0, 7]]])
        layer.fill_color = "blue"
        mesh._update_data()
        assert mesh.shared_program.vert["color_transform"] is color_function
    finally:
        visual.close()
