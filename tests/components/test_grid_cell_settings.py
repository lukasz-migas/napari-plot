"""Per-cell axis settings and limits of the plot grid."""

import numpy as np
import pytest

from napari_plot.components.canvas import PlotGridCell
from napari_plot.components.viewer_model import ViewerModel


def _grid_viewer(**grid: object) -> ViewerModel:
    viewer = ViewerModel()
    viewer.add_line([[0, 0], [10, 1]], name="first")
    viewer.add_line([[0, 0], [5, 100]], name="second")
    viewer.canvas.grid.update({"enabled": True, **grid})
    return viewer


def test_cell_overrides_and_reset() -> None:
    """Unset fields inherit the viewer; colors are normalized and sizes must be positive."""
    cell = PlotGridCell(row=0, column=1, label_color="red", x_visible=False, x_tick_rotation=45)
    np.testing.assert_allclose(cell.label_color, [1, 0, 0, 1])
    assert cell.overrides() == ("x_visible", "label_color", "x_tick_rotation")
    assert cell.overrides(("label_color", "tick_color")) == ("label_color",)

    cell.clear_overrides(("label_color",))
    assert cell.label_color is None
    assert cell.x_visible is False
    cell.clear_overrides()
    assert cell.overrides() == ()

    with pytest.raises(ValueError, match="greater than 0"):
        PlotGridCell(row=0, column=0, label_size=0)


def test_cell_rect_uses_own_limits_for_independent_axes() -> None:
    """Independent axes keep their own limits; shared axes go to the viewer camera."""
    viewer = _grid_viewer(sharex=False)
    assert set(viewer._grid_cells()) == {(0, 0), (0, 1)}
    events = []
    viewer.events.cell_rect.connect(events.append)

    viewer.set_cell_rect(0, 1, 1, 4, -5, 50)
    assert viewer.cell_rect(0, 1) == (1, 4, -5, 50)
    assert viewer.camera.rect[2:] == (-5, 50)
    assert viewer.cell_rect(0, 0)[2:] == (-5, 50)
    assert viewer.cell_rect(0, 0)[:2] == viewer.camera.rect[:2]
    assert [(event.cell, event.rect) for event in events] == [((0, 1), (1.0, 4.0, -5.0, 50.0))]

    # unchanged limits are not announced again
    viewer.set_cell_rect(0, 1, 1, 4, -5, 50)
    assert len(events) == 1


def test_cell_rect_with_shared_axes_sets_the_camera() -> None:
    viewer = _grid_viewer()
    viewer.set_cell_rect(0, 1, 2, 3, 4, 5)
    assert viewer.camera.rect == (2, 3, 4, 5)
    assert viewer.cell_rect(0, 0) == (2, 3, 4, 5)
    assert not viewer._cell_rects


@pytest.mark.parametrize(
    ("grid", "cell", "rect"),
    [
        ({"enabled": True}, (3, 3), (0, 1, 0, 1)),
        ({"enabled": False}, (0, 0), (0, 1, 0, 1)),
        ({"enabled": True, "joint": True}, (1, 0), (0, 1, 0, 1)),
        ({"enabled": True}, (0, 0), (1, 0, 0, 1)),
        ({"enabled": True}, (0, 0), (0, 1, 0, np.inf)),
    ],
)
def test_set_cell_rect_rejects_missing_cells_and_bad_limits(grid: dict, cell: tuple, rect: tuple) -> None:
    viewer = _grid_viewer(**grid)
    with pytest.raises(ValueError):
        viewer.set_cell_rect(*cell, *rect)


def test_cell_extent_uses_the_cell_layers_for_independent_axes() -> None:
    viewer = _grid_viewer(sharey=False)
    first, second = viewer._cell_extent(0, 0), viewer._cell_extent(0, 1)
    assert first[:2] == second[:2] == viewer.camera.extent[:2]
    assert first[3] < 10 < second[3]
