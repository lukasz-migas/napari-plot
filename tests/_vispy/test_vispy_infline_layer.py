import numpy as np
import pytest

from napari_plot._vispy.layers.infline import VispyInfLineLayer
from napari_plot.layers import InfLine


@pytest.fixture
def layer() -> InfLine:
    """Create an infinite-line layer with mixed orientations."""
    return InfLine(
        [1.0, 2.0, 3.0],
        orientation=["vertical", "horizontal", "vertical"],
        color=[
            (1.0, 0.0, 0.0, 1.0),
            (0.0, 1.0, 0.0, 1.0),
            (0.0, 0.0, 1.0, 1.0),
        ],
        width=2,
        opacity=0.5,
    )


def test_vispy_infline_layer_uses_fixed_subvisual_count(layer: InfLine) -> None:
    """Test stored infinite lines are rendered by one batched visual."""
    visual = VispyInfLineLayer(layer)

    assert len(visual.node._subvisuals) == 4
    np.testing.assert_allclose(visual.node.lines_visual.pos, [1.0, 2.0, 3.0])
    np.testing.assert_allclose(visual.node.lines_visual.orientation, [0.0, 1.0, 0.0])
    assert len(visual.node.lines_visual.vertex_pos) == 6


def test_vispy_infline_layer_builds_batched_vertices(layer: InfLine) -> None:
    """Test vertex data matches vertical and horizontal infinite-line layout."""
    visual = VispyInfLineLayer(layer)

    np.testing.assert_allclose(
        visual.node.lines_visual.vertex_pos,
        [
            [1.0, -1.0],
            [1.0, 1.0],
            [-1.0, 2.0],
            [1.0, 2.0],
            [3.0, -1.0],
            [3.0, 1.0],
        ],
    )
    np.testing.assert_allclose(
        visual.node.lines_visual.vertex_orientation,
        [0.0, 0.0, 1.0, 1.0, 0.0, 0.0],
    )


def test_vispy_infline_layer_refreshes_after_remove(layer: InfLine) -> None:
    """Test removing a line refreshes batched data without removing subvisuals."""
    visual = VispyInfLineLayer(layer)

    layer.selected_data = {1}
    layer.remove_selected()

    assert len(visual.node._subvisuals) == 4
    np.testing.assert_allclose(visual.node.lines_visual.pos, [1.0, 3.0])
    np.testing.assert_allclose(visual.node.lines_visual.orientation, [0.0, 0.0])


def test_vispy_infline_layer_highlight_updates_batched_colors(layer: InfLine) -> None:
    """Test selected lines are colored with the layer highlight color."""
    visual = VispyInfLineLayer(layer)

    layer.selected_data = {1}
    visual._on_appearance_change()

    np.testing.assert_allclose(visual.node.lines_visual.color[1], layer._highlight_color)
    np.testing.assert_allclose(
        visual.node.lines_visual.vertex_color[2:4],
        np.repeat(np.asarray([layer._highlight_color]), 2, axis=0),
    )


def test_vispy_infline_layer_width_and_opacity_propagate(layer: InfLine) -> None:
    """Test width and opacity are applied to batched and temporary line visuals."""
    visual = VispyInfLineLayer(layer)

    layer.width = 5
    visual.node.opacity = 0.25

    assert visual.node.lines_visual.line_width == 5
    assert visual.node.horizontal_visual.line_width == 5
    assert visual.node.vertical_visual.line_width == 5
    assert visual.node.lines_visual.opacity == 0.25
    assert visual.node.horizontal_visual.opacity == 0.25
    assert visual.node.vertical_visual.opacity == 0.25
