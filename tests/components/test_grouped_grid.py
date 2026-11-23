"""Metadata grouping in the canvas grid model."""

import numpy as np

from napari_plot.components.viewer_model import ViewerModel


def test_grouped_grid_layout_and_fallback() -> None:
    viewer = ViewerModel()
    a = viewer.add_line([[0, 0], [1, 1]], metadata={"napari_plot.group": "a"})
    b = viewer.add_image(np.zeros((2, 2)), metadata={"napari_plot.group": "b"})
    c = viewer.add_line([[0, 1], [1, 2]], metadata={"napari_plot.group": "a"})
    viewer.add_line([[0, 2], [1, 3]])
    grid = viewer.canvas.grid
    grid.enabled = True
    grid.shape = (1, 1)
    grid.stride = -2
    grid.spacing = 0.1
    native = list(grid.iter_viewboxes(viewer.layers))
    grid.group_by_metadata = True
    assert grid.actual_shape(viewer.layers) == (2, 2)
    assert list(grid.iter_viewboxes(viewer.layers)) == [((0, 0), (0, 2)), ((0, 1), (1,)), ((1, 0), (3,)), ((1, 1), ())]
    assert grid.position(2, viewer.layers) == (0, 0)
    assert grid.contents_at((0, 0), viewer.layers) == (0, 2)
    assert grid._compute_canvas_spacing((400, 200), viewer.layers) == 15
    a.visible = False
    assert grid.position(2, viewer.layers) == (0, 0)
    assert grid.position(1, viewer.layers) == (0, 1)
    c.visible = False
    b.visible = False
    assert list(grid.iter_viewboxes(viewer.layers)) == list(
        type(grid)(enabled=True, shape=(1, 1), stride=-2).iter_viewboxes(viewer.layers)
    )
    a.visible = b.visible = c.visible = True
    grid.group_by_metadata = False
    assert list(grid.iter_viewboxes(viewer.layers)) == native
    assert grid.shape == (1, 1)
    assert grid.stride == -2
    grid.enabled = False
    grid.group_by_metadata = True
    assert all(grid.position(i, viewer.layers) == (0, 0) for i in range(4))
