"""Test ViewerModel"""

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
    np.random.seed(0)
    data = np.random.random((10, 15))
    viewer.add_image(data)
    assert len(viewer.layers) == 1
    assert np.all(viewer.layers[0].data == data)


def test_add_points():
    """Test adding points."""
    viewer = ViewerModel()
    np.random.seed(0)
    data = 20 * np.random.random((10, 2))
    viewer.add_points(data)
    assert len(viewer.layers) == 1
    assert np.all(viewer.layers[0].data == data)


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
    np.random.seed(0)
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
    np.random.seed(0)
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
    np.random.seed(0)
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
    assert viewer.camera.extent == (x.min(), x.max(), y.min(), y.max())
    assert viewer.camera.extent == viewer.camera._extent == viewer.camera.get_effective_extent()

    # check x-range and make sure that it is always respected
    viewer.camera.set_x_range(None, 10)
    assert viewer.camera.get_effective_extent() == (x.min(), 10, y.min(), y.max())
    viewer.camera.set_x_range(-25, None)
    assert viewer.camera.get_effective_extent() == (-25, x.max(), y.min(), y.max())
    viewer.camera.x_range = (-10, 15)
    assert viewer.camera.get_effective_extent() == (-10, 15, y.min(), y.max())

    # make sure that x-range resets the effective extent
    viewer.camera.x_range = None
    assert viewer.camera.get_effective_extent() == (x.min(), x.max(), y.min(), y.max())

    # check x-range and make sure that it is always respected
    viewer.camera.set_y_range(None, 20)
    assert viewer.camera.get_effective_extent() == (x.min(), x.max(), y.min(), 20)
    viewer.camera.set_y_range(-20, None)
    assert viewer.camera.get_effective_extent() == (x.min(), x.max(), -20, y.max())
    viewer.camera.y_range = (-10, 15)
    assert viewer.camera.get_effective_extent() == (x.min(), x.max(), -10, 15)


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
    with pytest.raises(TypeError) as err:
        setattr(viewer, field, "test")

    assert "has allow_mutation set to False and cannot be assigned" in str(err.value)
