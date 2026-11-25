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


def test_joint_options_and_tick_formatters() -> None:
    viewer = ViewerModel()
    grid = JointGrid(viewer, size=80, autoscale=True)
    assert viewer.canvas.grid.joint_size == 80
    assert viewer.canvas.grid.joint_autoscale

    def formatter(value: float) -> str:
        return f"{value:.1e}"

    grid.set_tick_formatter(formatter, panel="top")
    assert viewer.canvas.grid.joint_top_tick_formatter is formatter
    assert viewer.canvas.grid.joint_right_tick_formatter is None
    grid.set_tick_formatter(None, panel="top")
    assert viewer.canvas.grid.joint_top_tick_formatter is None
    with pytest.raises(ValueError):
        grid.set_tick_formatter(formatter, panel="joint")
    with pytest.raises(ValueError):
        JointGrid(viewer, size=0)


def test_region_extent_of_lines_and_areas() -> None:
    """Layers report the value range of their data inside a range of either axis, in any data order."""
    import numpy as np

    from napari_plot.components._viewer_utils import get_layers_region_extent

    viewer = ViewerModel()
    x = np.linspace(0, 10, 11)
    line = viewer.add_line(np.c_[x, x**2])
    assert line._get_region_extent(0, 2, 4) == (4, 16)
    # a vertical trace: x holds the values, y the (unsorted) positions
    vertical = viewer.add_line(np.c_[[5, 1, 3], [9, 1, 5]])
    assert vertical._get_region_extent(1, 0, 6) == (1, 3)
    assert vertical._get_region_extent(1, 20, 30) == (None, None)

    multi = viewer.add_multi_line({"xs": [x], "ys": [x, 2 * x]})
    assert multi._get_region_extent(0, 0, 3) == (0, 6)
    assert multi._get_region_extent(1, 15, 30) == (8, 10)

    areas = viewer.add_areas([np.c_[x, np.zeros(11), x]], orientation="horizontal")
    # horizontal areas: t is y, the values are x
    assert areas._get_region_extent(1, 2, 3) == (0, 3)
    assert areas._get_region_extent(0, 9.5, 20) == (10, 10)

    assert get_layers_region_extent(0, 2, 4, [line, multi]) == (2, 16)
    line.visible = False
    assert get_layers_region_extent(0, 2, 4, [line]) == (None, None)


def test_value_range_in_region_includes_a_zero_baseline() -> None:
    import numpy as np

    viewer = ViewerModel()
    layer = viewer.add_line(np.c_[np.arange(5), [1, 2, 10, 2, 1]])
    assert viewer._get_value_range_in_region([layer], 0, 0, 1) == pytest.approx((0, 2.1))
    assert viewer._get_value_range_in_region([layer], 0, 0, 4, multiplier=1) == pytest.approx((0, 10))
    assert viewer._get_value_range_in_region([layer], 0, 10, 20) is None
    layer.data = np.c_[np.arange(5), -np.arange(5)]
    assert viewer._get_value_range_in_region([layer], 0, 0, 4, multiplier=1) == pytest.approx((-4, 0))
