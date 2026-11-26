"""Test ViewerModel"""

import inspect

import numpy as np
import pytest

from napari_plot.components.viewer_model import ViewerModel


def test_viewer_model():
    """Test instantiating viewer model."""
    viewer = ViewerModel()
    assert len(viewer.layers) == 0

    # Create viewer model with custom title
    viewer = ViewerModel(title="testing")
    assert viewer.title == "testing"


def test_add_image():
    """Test adding image."""
    viewer = ViewerModel()
    np.random.default_rng(0)
    data = np.random.random((10, 15))
    viewer.add_image(data)
    assert len(viewer.layers) == 1
    assert np.all(viewer.layers[0].data == data)


def test_status_from_cursor_uses_layer_slicing_state():
    """Status lookup supports napari's slicing-state based layers."""
    viewer = ViewerModel()
    viewer.add_image(np.arange(9).reshape(3, 3))
    viewer.mouse_over_canvas = True
    viewer.cursor.position = (1, 2)

    status, tooltip = viewer._calc_status_from_cursor()

    assert status["value"] == "5"
    assert tooltip == ""


def test_status_from_cursor_while_layer_is_unloaded():
    """Status and tooltip are hidden until the active slice is loaded."""
    viewer = ViewerModel()
    layer = viewer.add_labels(
        np.zeros((3, 3), dtype=np.uint8),
        features={"a": [1]},
    )
    viewer.mouse_over_canvas = True
    viewer.tooltip.visible = True
    viewer.cursor.position = (1, 2)
    loaded_status = viewer._calc_status_from_cursor()

    layer._slicing_state._set_loaded(False)
    assert viewer._calc_status_from_cursor() == ("Ready", "")

    layer._slicing_state._set_loaded(True)
    assert viewer._calc_status_from_cursor() == loaded_status
    assert loaded_status[1] == "0\na: 1"


def test_add_points():
    """Test adding points."""
    viewer = ViewerModel()
    np.random.default_rng(0)
    data = 20 * np.random.random((10, 2))
    viewer.add_points(data)
    assert len(viewer.layers) == 1
    assert np.all(viewer.layers[0].data == data)


def test_add_text():
    """Test adding text through the generated viewer API."""
    viewer = ViewerModel()
    data = np.array([[1, 2], [3, 4]])
    layer = viewer.add_text(data, ["a", "b"], size=20)

    assert len(viewer.layers) == 1
    np.testing.assert_array_equal(layer.data, data)
    np.testing.assert_array_equal(layer.text, ["a", "b"])
    assert layer.size == 20


def test_add_bar():
    """Test adding bars through the generated viewer API."""
    viewer = ViewerModel()
    layer = viewer.add_bar([2, 4], fill_color="red")

    assert len(viewer.layers) == 1
    np.testing.assert_array_equal(layer.data, [[0, 2], [1, 4]])


def test_add_empty_points_to_empty_viewer():
    viewer = ViewerModel()
    layer = viewer.add_points(name="empty points")
    assert layer.ndim == 2
    layer.add([1000.0, 27.0])
    assert layer.data.shape == (1, 2)


def test_add_empty_shapes_layer():
    viewer = ViewerModel()
    layer = viewer.add_shapes(ndim=2)
    assert layer.ndim == 2


def test_add_shapes():
    """Test adding shapes."""
    viewer = ViewerModel()
    np.random.default_rng(0)
    data = 20 * np.random.random((10, 4, 2))
    layer = viewer.add_shapes(data)
    assert len(viewer.layers) == 1
    assert len(layer.data) == 10


def test_new_shapes():
    """Test adding new shapes layer."""
    # Add labels to empty viewer
    viewer = ViewerModel()
    viewer.add_shapes()
    assert len(viewer.layers) == 1
    assert len(viewer.layers[0].data) == 0

    # Add points with image already present
    viewer = ViewerModel()
    np.random.default_rng(0)
    data = np.random.random((10, 15))
    viewer.add_image(data)
    layer = viewer.add_shapes()
    assert len(viewer.layers) == 2
    assert len(layer.data) == 0


def test_naming():
    """Test unique naming in LayerList."""
    viewer = ViewerModel()
    viewer.add_image(np.random.random((10, 10)), name="img")
    viewer.add_image(np.random.random((10, 10)), name="img")

    assert [lay.name for lay in viewer.layers] == ["img", "img [1]"]

    viewer.layers[1].name = "chg"
    assert [lay.name for lay in viewer.layers] == ["img", "chg"]

    viewer.layers[0].name = "chg"
    assert [lay.name for lay in viewer.layers] == ["chg [1]", "chg"]


def test_selection():
    """Test only last added is selected."""
    viewer = ViewerModel()
    viewer.add_image(np.random.random((10, 10)))
    assert viewer.layers[0] in viewer.layers.selection

    viewer.add_image(np.random.random((10, 10)))
    assert viewer.layers.selection == {viewer.layers[-1]}

    viewer.add_image(np.random.random((10, 10)))
    assert viewer.layers.selection == {viewer.layers[-1]}

    viewer.layers.selection.update(viewer.layers)
    viewer.add_image(np.random.random((10, 10)))
    assert viewer.layers.selection == {viewer.layers[-1]}


def test_active_layer():
    """Test active layer is correct as layer selections change."""
    viewer = ViewerModel()
    np.random.default_rng(0)
    # Check no active layer present
    assert viewer.layers.selection.active is None

    # Check added layer is active
    viewer.add_image(np.random.random((5, 5)))
    assert len(viewer.layers) == 1
    assert viewer.layers.selection.active == viewer.layers[0]

    # Check newly added layer is active
    viewer.add_image(np.random.random((5, 6)))
    assert len(viewer.layers) == 2
    assert viewer.layers.selection.active == viewer.layers[1]

    # Check no active layer after unselecting all
    viewer.layers.selection.clear()
    assert viewer.layers.selection.active is None

    # Check selected layer is active
    viewer.layers.selection.add(viewer.layers[0])
    assert viewer.layers.selection.active == viewer.layers[0]

    # Check no layer is active if both layers are selected
    viewer.layers.selection.add(viewer.layers[1])
    assert viewer.layers.selection.active is None


def test_camera():
    """Test camera."""
    viewer = ViewerModel()
    x, y = np.arange(10), -np.arange(10)
    data = np.c_[x, y]
    viewer.add_line(data)
    assert len(viewer.layers) == 1
    # the extent is padded by half the line width (in screen pixels) so the line at the data edge is not clipped
    x_min, x_max, y_min, y_max = viewer.camera.extent
    assert x_min < x.min()
    assert y_min < y.min()
    assert x_max > x.max()
    assert y_max > y.max()
    np.testing.assert_allclose(viewer.camera.extent, (x.min(), x.max(), y.min(), y.max()), atol=0.05)
    assert viewer.camera.extent == viewer.camera._extent == viewer.camera.get_effective_extent()

    # check x-range and make sure that it is always respected
    viewer.camera.set_x_range(None, 10)
    assert viewer.camera.get_effective_extent() == (x_min, 10, y_min, y_max)
    viewer.camera.set_x_range(-25, None)
    assert viewer.camera.get_effective_extent() == (-25, x_max, y_min, y_max)
    viewer.camera.x_range = (-10, 15)
    assert viewer.camera.get_effective_extent() == (-10, 15, y_min, y_max)

    # make sure that x-range resets the effective extent
    viewer.camera.x_range = None
    assert viewer.camera.get_effective_extent() == (x_min, x_max, y_min, y_max)

    # check x-range and make sure that it is always respected
    viewer.camera.set_y_range(None, 20)
    assert viewer.camera.get_effective_extent() == (x_min, x_max, y_min, 20)
    viewer.camera.set_y_range(-20, None)
    assert viewer.camera.get_effective_extent() == (x_min, x_max, -20, y_max)
    viewer.camera.y_range = (-10, 15)
    assert viewer.camera.get_effective_extent() == (x_min, x_max, -10, 15)


def test_log_extent_uses_smallest_positive_values() -> None:
    viewer = ViewerModel()
    viewer.add_line(np.asarray([[0.0, 0.0], [1.0, 0.1], [10.0, 100.0]]))

    viewer.axis.x_scale = "log"
    viewer.axis.y_scale = "log"

    assert viewer._get_rect_extent() == (1.0, 10.0, 0.1, 100.0)


def test_categorical_extent_keeps_numeric_layer_range() -> None:
    viewer = ViewerModel()
    viewer.add_line(np.asarray([[-2.0, -3.0], [0.0, 1.0], [2.0, 5.0]]))

    viewer.axis.x_categories = ["left", "middle", "right"]
    viewer.axis.y_categories = ["low", "middle", "high"]

    assert viewer._get_rect_extent() == (-2.0, 2.0, -3.0, 5.0)


def test_custom_add_methods_are_registered():
    """Test custom napari-plot layer add methods can be imported and called."""
    signature = inspect.signature(ViewerModel.add_line)
    assert list(signature.parameters)[:2] == ["self", "data"]
    assert signature.return_annotation.__name__ == "Line"

    viewer = ViewerModel()
    data = np.array([[0, 0], [1, 1]])
    layer = viewer.add_line(data, color="red")

    assert layer is viewer.layers[0]
    assert np.array_equal(layer.data, data)


@pytest.mark.parametrize(
    "field",
    ["camera", "cursor", "layers", "axis", "drag_tool"],
)
def test_not_mutable_fields(field):
    """Test appropriate fields are not mutable."""
    viewer = ViewerModel()

    # Check attribute lives on the viewer
    assert hasattr(viewer, field)
    # Check attribute does not have an event emitter
    assert not hasattr(viewer.events, field)

    # Check attribute is not settable
    with pytest.raises((TypeError, ValueError)) as err:
        setattr(viewer, field, "test")

    assert "Field is frozen" in str(err.value)


def test_reset_current_y_view_keeps_y_for_scatter() -> None:
    """Scatter layers cannot report y for an x-window, so the current y-axis view must be kept."""
    viewer = ViewerModel()
    viewer.add_scatter(np.asarray([[-1.0, -1.0], [1.0, 1.0]]))
    viewer.camera.rect = (-4.0, 4.0, -8.0, 8.0)
    viewer.reset_current_y_view()
    assert viewer.camera.rect == (-4.0, 4.0, -8.0, 8.0)


@pytest.mark.parametrize(
    ("y", "expected"),
    [
        ([1.0, 10.0], (0.0, 10.5)),  # positive - baseline stays at 0
        ([-10.0, -1.0], (-10.5, 0.0)),  # negative - baseline stays at 0
        ([-5.0, 5.0], (-5.5, 5.5)),  # signed - both ends padded
    ],
)
def test_reset_current_y_view_pads_data_ends(y, expected) -> None:
    viewer = ViewerModel()
    viewer.add_centroids(np.c_[[1.0, 2.0], y])
    viewer.camera.rect = (0.0, 3.0, 0.0, 1.0)
    viewer.reset_current_y_view()
    np.testing.assert_allclose(viewer.camera.rect, (0.0, 3.0, *expected))


def test_image_extent_includes_half_pixel_edges() -> None:
    """Images are drawn with pixels centered on their indices, so the extent reaches the pixel edges."""
    viewer = ViewerModel()
    viewer.camera.extent_mode = "restricted"
    viewer.add_image(np.zeros((2, 4)))
    assert viewer._get_rect_extent() == (-0.5, 3.5, -0.5, 1.5)
    viewer.reset_view()
    assert viewer.camera.rect == (-0.5, 3.5, -0.5, 1.5)


def test_extent_leaves_room_for_pixel_sized_markers() -> None:
    """Markers sized in screen pixels at the data edge are not clipped."""
    viewer = ViewerModel()
    viewer._canvas_size = (220, 420)
    viewer.add_scatter(np.asarray([[0.0, 0.0], [1.0, 1.0]]), size=20, scaling=False, border_width=0)
    xmin, xmax, ymin, ymax = viewer._get_rect_extent()
    # 10 px on each side of a 400 px (x) / 200 px (y) usable canvas
    np.testing.assert_allclose((xmin, xmax, ymin, ymax), (-0.025, 1.025, -0.05, 1.05))


def test_limits_support_inversion_and_reset_each_axis() -> None:
    viewer = ViewerModel()
    viewer.add_line([[0, 0], [10, 12]])
    viewer.xlim = (8, 2)
    viewer.ylim = (1, 9)

    assert viewer.axis.x_inverted
    assert viewer.xlim == (8, 2)
    assert viewer.camera.rect == (2, 8, 1, 9)

    viewer.xlim = None
    assert viewer.xlim == viewer._get_rect_extent()[:2][::-1]
    assert viewer.ylim == (1, 9)


def test_autoscale_updates_fitted_axes_and_preserves_manual_limits() -> None:
    viewer = ViewerModel()
    line = viewer.add_line([[0, 0], [10, 10]])
    viewer.xlim = (2, 8)
    viewer.margins = (0.0, 0.1)
    assert viewer.xlim == (2, 8)
    assert viewer.ylim[1] > 11

    first_ylim = viewer.ylim
    viewer.autoscale = False
    line.data = [[0, 0], [20, 20]]
    assert viewer.ylim == first_ylim
    viewer.autoscale = True
    assert viewer.camera.rect == viewer.camera.extent


def test_empty_cell_extent_is_independent_of_other_layers() -> None:
    viewer = ViewerModel()
    viewer.add_line([[10, 20], [40, 50]])
    assert viewer._get_rect_extent(layers=[]) == (-0.5, 0.5, -0.5, 0.5)


def test_extent_padding_keeps_positive_data_positive() -> None:
    """Padding never pushes strictly positive data below zero, so switching to a log axis stays valid."""
    viewer = ViewerModel()
    viewer.add_line(np.asarray([[0.001, 0.001], [10.0, 10.0]]), width=20)
    xmin, _, ymin, _ = viewer._get_rect_extent()
    assert xmin == ymin == 0.001


def test_appearance_and_zoom_events_do_not_recompute_the_extent(monkeypatch: pytest.MonkeyPatch):
    """Layer events that never move data (image appearance, zoom level) skip the extent update; data changes do not."""
    viewer = ViewerModel()
    image = viewer.add_image(np.random.random((10, 10)))
    calls = []
    original = ViewerModel._get_rect_extent
    monkeypatch.setattr(
        ViewerModel, "_get_rect_extent", lambda self, **kwargs: calls.append(1) or original(self, **kwargs)
    )
    image.contrast_limits = (0.1, 0.9)
    image.colormap = "magma"
    image.gamma = 0.5
    image.events.scale_factor()
    assert calls == []
    image.data = np.random.random((20, 20))
    assert calls
