"""Tests for joint plot model placement."""

import pytest

from napari_plot import JointGrid
from napari_plot.components.viewer_model import ViewerModel


def test_joint_placement_and_mode_switch() -> None:
    viewer = ViewerModel()
    main = viewer.add_line([[0, 0], [1, 1]], metadata={"group": "keep"})
    top = viewer.add_line([[0, 2], [1, 3]])
    grid = JointGrid(viewer, right=False)
    grid.add_layer(top, panel="top")
    assert grid.layers == [top]
    assert main.metadata["group"] == "keep"
    assert dict(viewer.canvas.grid.iter_viewboxes(viewer.layers)) == {(0, 0): (1,), (1, 0): (0,)}
    with pytest.raises(ValueError):
        grid.add_layer(main, panel="right")
    viewer.reset_plot()
    assert not viewer.canvas.grid.joint


def test_joint_validation() -> None:
    viewer = ViewerModel()
    with pytest.raises(ValueError):
        JointGrid(viewer, top=False, right=False)
    with pytest.raises(ValueError):
        JointGrid(viewer, ratio=0)


def test_shared_fit_and_disabled_panel_fallback() -> None:
    viewer = ViewerModel()
    main = viewer.add_line([[0, 0], [1, 1]])
    top = viewer.add_line([[0, 100], [10, 200]])
    right = viewer.add_line([[100, 0], [200, 20]])
    grid = JointGrid(viewer)
    grid.add_layer(top, panel="top")
    grid.add_layer(right, panel="right")
    viewer.reset_view()
    assert viewer.camera.rect[1] < 20
    assert viewer.camera.rect[3] < 30
    top.visible = False
    assert viewer.camera.extent[1] < 2
    top.visible = True
    JointGrid(viewer, right=False)
    assert viewer.canvas.grid._positions(viewer.layers)[2] == (1, 0)
    assert main in viewer.layers


def test_native_layer_changes_and_facet_takeover() -> None:
    import numpy as np

    from napari_plot.stats.facets import FacetGrid

    viewer = ViewerModel()
    image = viewer.add_image(np.ones((2, 2)))
    grid = JointGrid(viewer)
    grid.add_layer(image, panel="top")
    viewer.reset_view()
    image.data = np.ones((2, 12))
    assert viewer.camera.extent[1] > 10
    image.visible = False
    assert viewer.camera.extent[1] < 2
    FacetGrid(viewer)._configure()
    assert not viewer.canvas.grid.joint
