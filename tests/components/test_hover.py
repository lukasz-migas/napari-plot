"""Crosshair, hover readout and status coordinates driven by the cursor."""

import numpy as np
import pytest

from napari_plot.components.viewer_model import ViewerModel


@pytest.fixture
def viewer() -> ViewerModel:
    viewer = ViewerModel()
    viewer.axis.x_label, viewer.axis.y_label = "Time", "Counts"
    viewer.add_line(np.c_[np.arange(10.0), np.arange(10.0) ** 2], name="square")
    viewer.add_line(np.c_[np.arange(10.0), np.arange(10.0)], name="linear")
    viewer.canvas.size = (400, 600)
    viewer.camera.rect = (0.0, 10.0, 0.0, 100.0)
    return viewer


def _hover(viewer: ViewerModel, x: float, y: float) -> None:
    viewer.mouse_over_canvas = True
    viewer.cursor.position = (y, x)


def test_overlays_are_hidden_by_default(viewer: ViewerModel) -> None:
    assert not viewer.crosshair.visible
    assert not viewer.hover.visible
    _hover(viewer, 3.0, 8.0)
    assert viewer.crosshair.point is None
    assert viewer.hover.text == ""


def test_hover_readout_snaps_to_closest_curve(viewer: ViewerModel) -> None:
    viewer.hover.visible = viewer.crosshair.visible = True
    _hover(viewer, 3.0, 8.0)
    assert viewer.crosshair.point == (3.0, 9.0)
    assert viewer.hover.text == "Time: 3\nsquare: 9\nlinear: 3"

    _hover(viewer, 3.0, 2.0)
    assert viewer.crosshair.point == (3.0, 3.0)
    assert viewer.hover.text.splitlines()[1] == "linear: 3"

    viewer.hover.formatter = lambda info: f"{info.label}@{info.x:g}"
    _hover(viewer, 3.0, 2.0)
    assert viewer.hover.text == "linear@3"

    # outside the data the readout empties and the crosshair follows the cursor
    _hover(viewer, 50.0, 2.0)
    assert viewer.hover.text == ""
    assert viewer.crosshair.point == (50.0, 2.0)

    viewer.mouse_over_canvas = False
    assert viewer.crosshair.point is None
    assert viewer.hover.text == ""


def test_crosshair_follows_cursor_unless_snapping(viewer: ViewerModel) -> None:
    viewer.crosshair.visible = True
    _hover(viewer, 3.2, 8.0)
    assert viewer.crosshair.point == (3.2, 8.0)
    viewer.crosshair.snap_to_data = True
    assert viewer.crosshair.point == (3.0, 9.0)
    viewer.crosshair.visible = False
    assert viewer.crosshair.point is None


def test_hidden_layers_are_ignored(viewer: ViewerModel) -> None:
    viewer.layers["square"].visible = False
    info = viewer.hover_info(3.0, 8.0)
    assert info is not None
    assert (info.label, info.rows) == ("linear", ())


def test_status_shows_x_y_coordinates(viewer: ViewerModel) -> None:
    _hover(viewer, 3.2, 8.0)
    viewer.layers.selection.active = viewer.layers["square"]
    status, _ = viewer._calc_status_from_cursor()
    assert status["coordinates"] == "x=3.2, y=8: 9"

    viewer.layers.selection.clear()
    assert viewer._calc_status_from_cursor() == ("x=3.2, y=8", "")
