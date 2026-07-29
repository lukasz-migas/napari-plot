import numpy as np
import pytest
from napari._vispy.utils.qt_font import FontInfo

from napari_plot._vispy.layers.region import VispyRegionLayer
from napari_plot.layers import Region


@pytest.fixture
def layer() -> Region:
    """Create a region layer with mixed orientations."""
    return Region(
        [
            ((1.0, 3.0), "vertical"),
            ((2.0, 5.0), "horizontal"),
            ((6.0, 7.0), "vertical"),
        ],
        color=[
            (1.0, 0.0, 0.0, 1.0),
            (0.0, 1.0, 0.0, 1.0),
            (0.0, 0.0, 1.0, 1.0),
        ],
        opacity=0.5,
    )


def test_vispy_region_layer_uses_fixed_subvisual_count(layer: Region) -> None:
    """Test stored regions are rendered by one batched visual."""
    visual = VispyRegionLayer(layer, font_info=FontInfo())

    assert len(visual.node._subvisuals) == 4
    np.testing.assert_allclose(visual.node.regions_visual.pos, [[1.0, 3.0], [2.0, 5.0], [6.0, 7.0]])
    np.testing.assert_allclose(visual.node.regions_visual.orientation, [0.0, 1.0, 0.0])
    assert len(visual.node.regions_visual.vertex_pos) == 12


def test_vispy_region_layer_builds_batched_vertices_and_indices(layer: Region) -> None:
    """Test vertex data matches vertical and horizontal infinite-region layout."""
    visual = VispyRegionLayer(layer, font_info=FontInfo())

    np.testing.assert_allclose(
        visual.node.regions_visual.vertex_pos,
        [
            [1.0, -1.0],
            [1.0, 1.0],
            [3.0, -1.0],
            [3.0, 1.0],
            [1.0, 2.0],
            [-1.0, 2.0],
            [1.0, 5.0],
            [-1.0, 5.0],
            [6.0, -1.0],
            [6.0, 1.0],
            [7.0, -1.0],
            [7.0, 1.0],
        ],
    )
    np.testing.assert_array_equal(
        visual.node.regions_visual.indices,
        [0, 1, 2, 1, 2, 3, 4, 5, 6, 5, 6, 7, 8, 9, 10, 9, 10, 11],
    )
    np.testing.assert_allclose(
        visual.node.regions_visual.vertex_orientation,
        [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
    )


def test_vispy_region_layer_refreshes_after_remove(layer: Region) -> None:
    """Test removing a region refreshes batched data without removing subvisuals."""
    visual = VispyRegionLayer(layer, font_info=FontInfo())

    layer.selected_data = {1}
    layer.remove_selected()

    assert len(visual.node._subvisuals) == 4
    np.testing.assert_allclose(visual.node.regions_visual.pos, [[1.0, 3.0], [6.0, 7.0]])
    np.testing.assert_allclose(visual.node.regions_visual.orientation, [0.0, 0.0])


def test_vispy_region_layer_highlight_updates_batched_colors(layer: Region) -> None:
    """Test selected regions are colored with the layer highlight color."""
    visual = VispyRegionLayer(layer, font_info=FontInfo())

    layer.selected_data = {1}
    visual._on_appearance_change()

    np.testing.assert_allclose(visual.node.regions_visual.color[1], layer._highlight_color)
    np.testing.assert_allclose(
        visual.node.regions_visual.vertex_color[4:8],
        np.repeat(np.asarray([layer._highlight_color]), 4, axis=0),
    )


def test_vispy_region_layer_opacity_propagates(layer: Region) -> None:
    """Test opacity is applied to batched and temporary region visuals."""
    visual = VispyRegionLayer(layer, font_info=FontInfo())

    visual.node.opacity = 0.25

    assert visual.node.regions_visual.opacity == 0.25
    assert visual.node.horizontal_visual.opacity == 0.25
    assert visual.node.vertical_visual.opacity == 0.25
