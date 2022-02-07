"""Regions."""
import numpy as np
import pytest

from napari_plot.layers.region import Region


def test_empty_regions():
    layer = Region(None)
    assert layer.ndim == 2


def test_default_region():
    # add multiple regions
    data = [[25, 50], [80, 90]]
    layer = Region(data)
    assert layer.n_regions == len(data)
    assert np.all([o == "vertical" for o in layer.orientation])

    # add single region
    data = [[25, 50]]
    layer = Region(data)
    assert layer.n_regions == len(data)
    assert np.all([o == "vertical" for o in layer.orientation])


def test_vertical_region():
    # add multiple regions
    data = [[25, 50], [80, 90]]
    layer = Region(data, orientation="vertical")
    assert layer.n_regions == len(data)
    assert np.all([o == "vertical" for o in layer.orientation])

    # add single region
    data = [[25, 50]]
    layer = Region(data, orientation="vertical")
    assert layer.n_regions == len(data)
    assert np.all([o == "vertical" for o in layer.orientation])


def test_horizontal_region():
    # add multiple regions
    data = [[25, 50], [80, 90]]
    layer = Region(data, orientation="horizontal")
    assert layer.n_regions == len(data)
    assert np.all([o == "horizontal" for o in layer.orientation])

    # add single region
    data = [[25, 50]]
    layer = Region(data, orientation="horizontal")
    assert layer.n_regions == len(data)
    assert np.all([o == "horizontal" for o in layer.orientation])


def test_with_orientation():
    # add multiple regions
    data = [([25, 50], "vertical")]
    layer = Region(data)
    assert layer.n_regions == len(data)
    assert np.all([o == "vertical" for o in layer.orientation])

    data = [([25, 50], "horizontal")]
    layer = Region(data)
    assert layer.n_regions == len(data)
    assert np.all([o == "horizontal" for o in layer.orientation])


def test_with_tuples():
    # add multiple regions
    data = [(50, 100), (100, 150), (300, 321)]
    layer = Region(data)
    assert layer.n_regions == len(data)
    assert np.all([o == "vertical" for o in layer.orientation])

    layer = Region(data, orientation="horizontal")
    assert layer.n_regions == len(data)
    assert np.all([o == "horizontal" for o in layer.orientation])


def test_adding_regions():
    data = [[25, 50], [50, 100]]
    layer = Region(data, orientation="vertical")
    assert layer.n_regions == len(data)
    assert layer.ndim == 2

    new_data = [[75, 123], [142, 143]]
    layer.add(new_data, orientation="horizontal")
    assert layer.n_regions == len(data + new_data)


def test_region_color_default():
    data = [[25, 50], [50, 100]]
    layer = Region(data, orientation="vertical")
    assert layer.n_regions == len(data)
    assert layer.ndim == 2
    np.testing.assert_array_equal(layer.face_color[0], np.asarray([1.0, 1.0, 1.0, 1.0]))


@pytest.mark.parametrize("color", ["red", "#FF0000", (1, 0, 0), (1, 0, 0, 1)])
def test_region_color_set(color):
    data = [[25, 50], [50, 100]]
    layer = Region(data, orientation="vertical", face_color=color)
    assert layer.n_regions == len(data)
    assert layer.ndim == 2
    np.testing.assert_array_equal(layer.face_color[0], np.asarray([1.0, 0.0, 0.0, 1.0]))


def test_region_color_current():
    data = 20 * [np.random.random((2, 1))]
    layer = Region(data, orientation="vertical")
    np.testing.assert_array_equal(layer.face_color[0], np.asarray([1.0, 1.0, 1.0, 1.0]))

    layer.selected_data = {0, 1}
    assert layer.selected_data == {0, 1}
    layer.current_face_color = "red"
    np.testing.assert_array_equal(layer.face_color[1], np.asarray([1.0, 0.0, 0.0, 1.0]))
    np.testing.assert_array_equal(layer.face_color[2], np.asarray([1.0, 1.0, 1.0, 1.0]))

    layer.selected_data = {9}
    assert layer.selected_data == {9}
    layer.current_face_color = "#00FF00"
    np.testing.assert_array_equal(layer.face_color[5], np.asarray([1.0, 1.0, 1.0, 1.0]))
    np.testing.assert_array_equal(layer.face_color[9], np.asarray([0.0, 1.0, 0.0, 1.0]))


def test_region_selection():
    data = 20 * [np.random.random((2, 1))]
    layer = Region(data, orientation="vertical")
    layer.selected_data = {0, 1}
    assert layer.selected_data == {0, 1}

    layer.selected_data = {9}
    assert layer.selected_data == {9}

    layer.selected_data = set()
    assert layer.selected_data == set()


def test_thumbnail():
    """Test the image thumbnail for square data."""
    data = [[25, 50], [50, 100]]
    layer = Region(data, orientation="vertical")
    assert layer.n_regions == len(data)
    assert layer.ndim == 2
    layer._update_thumbnail()
    assert layer.thumbnail.shape == layer._thumbnail_shape


def test_region_trim():
    data = np.random.random((20, 2))
    layer = Region(data)
    assert layer.n_regions == 20
    data = np.random.random((10, 2))
    layer.data = data
    assert layer.n_regions == 10


def test_z_index():
    """Test setting z-index during instantiation."""
    shape = (10, 2)
    data = 20 * np.random.random(shape)
    layer = Region(data)
    assert layer.z_index == [0] * shape[0]

    # Instantiate with custom z-index
    layer = Region(data, z_index=4)
    assert layer.z_index == [4] * shape[0]

    # Instantiate with custom z-index list
    z_index_list = [2, 3] * 5
    layer = Region(data, z_index=z_index_list)
    assert layer.z_index == z_index_list

    # Add new shape and its z-index
    new_shape = np.random.random((1, 2))
    layer.add(new_shape)
    assert len(layer.z_index) == shape[0] + 1
    assert layer.z_index == z_index_list + [4]

    # Check removing data adjusts colors correctly
    layer.selected_data = {0, 2}
    layer.remove_selected()
    assert len(layer.data) == shape[0] - 1
    assert len(layer.z_index) == shape[0] - 1
    assert layer.z_index == [z_index_list[1]] + z_index_list[3:] + [4]

    # Test setting index with number
    layer.z_index = 4
    assert all([idx == 4 for idx in layer.z_index])

    # Test setting index with list
    new_z_indices = [2] * 5 + [3] * 4
    layer.z_index = new_z_indices
    assert layer.z_index == new_z_indices

    # Test setting with incorrect size list throws error
    new_z_indices = [2, 3]
    with pytest.raises(ValueError):
        layer.z_index = new_z_indices


def test_move_to_front():
    """Test moving shapes to front."""
    data = 20 * np.random.random((10, 2))
    z_index_list = [2, 3] * 5
    layer = Region(data, z_index=z_index_list)
    assert layer.z_index == z_index_list

    # Move selected shapes to front
    layer.selected_data = {0, 2}
    layer.move_to_front()
    assert layer.z_index == [4] + [z_index_list[1]] + [4] + z_index_list[3:]


def test_move_to_back():
    """Test moving shapes to back."""
    shape = (10, 2)
    np.random.seed(0)
    data = 20 * np.random.random(shape)
    z_index_list = [2, 3] * 5
    layer = Region(data, z_index=z_index_list)
    assert layer.z_index == z_index_list

    # Move selected shapes to front
    layer.selected_data = {0, 2}
    layer.move_to_back()
    assert layer.z_index == [1] + [z_index_list[1]] + [1] + z_index_list[3:]
