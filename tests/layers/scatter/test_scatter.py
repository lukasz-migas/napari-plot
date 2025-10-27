"""Test scatter layer."""

from itertools import cycle, islice

import numpy as np
import pandas as pd
import pytest

from napari_plot.layers import Scatter


def _make_cycled_properties(values, length):
    """Helper function to make property values

    Parameters
    ----------
    values
        The values to be cycled.
    length : int
        The length of the resulting property array

    Returns
    -------
    cycled_properties : np.ndarray
        The property array comprising the cycled values.
    """
    cycled_properties = np.array(list(islice(cycle(values), 0, length)))
    return cycled_properties


def test_scatter_empty():
    layer = Scatter()
    assert layer.ndim == 2
    assert layer.data.shape == (0, 2)


def test_scatter_update_attrs():
    layer = Scatter()
    # normally update attributes
    layer.update_attributes(name="test", metadata={"test": "test"})
    assert layer.name == "test"
    assert layer.metadata == {"test": "test"}

    # test bad attributes
    with pytest.raises(AttributeError):
        layer.update_attributes(not_real_attr="test")
    layer.update_attributes(not_real_attr="test", throw_exception=False)
    assert not hasattr(layer, "not_real_attr")

    # test bad values
    with pytest.raises(ValueError):
        layer.update_attributes(face_color=1)
    layer.update_attributes(face_color=1, throw_exception=False)


@pytest.mark.parametrize("data", [[[0, 1], [1, 2], [3, 3]], np.random.random((10, 2))])
def test_scatter_data(data):
    layer = Scatter(data)
    assert isinstance(layer.data, np.ndarray)
    with pytest.raises(ValueError):
        layer.data = np.random.random((10, 3))


@pytest.mark.parametrize("data", [[[0, 1, 2], [1, 2, 3]], np.random.random((10, 3))])
def test_scatter_data_fail(data):
    with pytest.raises(ValueError):
        Scatter(data)


def test_scatter_change_data():
    data = np.random.random((10, 2))
    layer = Scatter(data)
    np.testing.assert_array_equal(layer.x, data[:, 1])
    np.testing.assert_array_equal(layer.y, data[:, 0])

    new_data = np.random.random(10)
    layer.x = new_data
    layer.y = new_data

    new_data = np.random.random((10, 2))
    with pytest.raises(ValueError):
        layer.x = new_data
    with pytest.raises(ValueError):
        layer.y = new_data

    data = np.random.random((20, 2))
    layer.data = data
    with pytest.raises(ValueError):
        layer.x = new_data
    with pytest.raises(ValueError):
        layer.y = new_data


def test_scatter_edge_width():
    data = np.random.random((10, 2))
    layer = Scatter(data, border_width=4, border_width_is_relative=False)
    layer.border_width = 3
    assert np.all(layer.border_width == 3)
    layer.border_width = np.arange(len(data))
    assert layer.border_width[0] == 0
    assert layer.border_width[3] == 3

    new_data = np.random.random((0, 2))
    layer.data = new_data
    assert len(layer.border_width) == len(new_data)

    new_data = np.random.random((30, 2))
    layer.data = new_data
    assert len(layer.border_width) == len(new_data)

    # check with `edge_width_is_relative=True`
    data = np.random.random((10, 2))
    layer = Scatter(data)
    layer.border_width = 0.5
    assert np.all(layer.border_width == 0.5)

    # raised because `edge_width_is_relative=True` which expects values between 0 and 1
    with pytest.raises(ValueError):
        layer.border_width = 3

    layer.border_width_is_relative = False
    layer.border_width = 3
    assert np.all(layer.border_width == 3)


def test_scatter_size():
    data = np.random.random((10, 2))
    layer = Scatter(data)
    layer.size = 3
    assert np.all(layer.size == 3)
    layer.size = np.arange(len(data))
    np.testing.assert_array_equal(layer.size[0], np.asarray([0, 0]))
    np.testing.assert_array_equal(layer.size[3], np.asarray([3, 3]))

    new_data = np.random.random((0, 2))
    layer.data = new_data
    assert len(layer.size) == len(new_data)

    new_data = np.random.random((30, 2))
    layer.data = new_data
    assert len(layer.size) == len(new_data)


def test_scatter_color():
    data = np.random.random((10, 2))
    layer = Scatter(data, face_color="white", border_color="red")
    assert len(layer.face_color) == len(data)
    assert len(layer.border_color) == len(data)
    np.testing.assert_array_equal(layer.face_color[0], np.asarray([1.0, 1.0, 1.0, 1.0]))
    np.testing.assert_array_equal(
        layer.border_color[5], np.asarray([1.0, 0.0, 0.0, 1.0])
    )

    layer.border_color = np.asarray([1.0, 1.0, 1.0, 1.0])
    np.testing.assert_array_equal(
        layer.border_color[0], np.asarray([1.0, 1.0, 1.0, 1.0])
    )
    layer.face_color = np.asarray([1.0, 0.0, 0.0, 1.0])
    np.testing.assert_array_equal(layer.face_color[4], np.asarray([1.0, 0.0, 0.0, 1.0]))

    # add new dataset with FEWER items
    data = np.random.random((0, 2))
    layer.data = data
    assert len(layer.face_color) == len(data)
    assert len(layer.border_color) == len(data)

    # add new dataset with MORE items
    data = np.random.random((12, 2))
    layer.data = data
    assert len(layer.face_color) == len(data)
    assert len(layer.border_color) == len(data)

    # set new colors
    layer.face_color = np.random.random((12, 4))
    assert len(layer.face_color) == len(data)
    assert layer.face_color.shape == (12, 4)
    layer.border_color = "yellow"
    assert len(layer.border_color) == len(data)


def test_empty_points_with_properties():
    """Test instantiating an empty Points layer with properties

    See: https://github.com/napari/napari/pull/1069
    """
    properties = {
        "label": np.array(["label1", "label2"]),
        "cont_prop": np.array([0], dtype=float),
    }
    layer = Scatter(property_choices=properties)
    current_props = {k: v[0] for k, v in properties.items()}
    np.testing.assert_equal(layer.current_properties, current_props)

    # verify the property datatype is correct
    assert layer.properties["cont_prop"].dtype == float


def test_empty_points_with_properties_list():
    """Test instantiating an empty Points layer with properties
    stored in a list

    See: https://github.com/napari/napari/pull/1069
    """
    properties = {"label": ["label1", "label2"], "cont_prop": [0]}
    layer = Scatter(property_choices=properties)
    current_props = {k: np.asarray(v[0]) for k, v in properties.items()}
    np.testing.assert_equal(layer.current_properties, current_props)


def test_empty_layer_with_text_properties():
    """Test initializing an empty layer with text defined"""
    default_properties = {"point_type": np.array([1.5], dtype=float)}
    text_kwargs = {"string": "point_type", "color": "red"}
    layer = Scatter(
        property_choices=default_properties,
        text=text_kwargs,
    )
    assert layer.text.values.size == 0
    # np.testing.assert_allclose(layer.text.color.constant, [1, 0, 0, 1])

    # add a point and check that the appropriate text value was added
    layer.add([1, 1])
    np.testing.assert_equal(layer.text.values, ["1.5"])
    # np.testing.assert_allclose(layer.text.color.constant, [1, 0, 0, 1])


def test_empty_layer_with_text_formatted():
    """Test initializing an empty layer with text defined"""
    default_properties = {"point_type": np.array([1.5], dtype=float)}
    layer = Scatter(
        property_choices=default_properties,
        text="point_type: {point_type:.2f}",
    )
    assert layer.text.values.size == 0
    layer.add([1, 1])
    # add a point and check that the appropriate text value was added
    np.testing.assert_equal(layer.text.values, ["point_type: 1.50"])


def test_properties_dataframe():
    """Test if properties can be provided as a DataFrame"""
    shape = (10, 2)
    np.random.seed(0)
    data = 20 * np.random.random(shape)
    properties = {"point_type": _make_cycled_properties(["A", "B"], shape[0])}
    properties_df = pd.DataFrame(properties)
    properties_df = properties_df.astype(properties["point_type"].dtype)
    layer = Scatter(data, properties=properties_df)
    np.testing.assert_equal(layer.properties, properties)


def test_point_selection_by_path():
    """Test which indices are being selected by a path."""
    x = np.arange(0.0, 10.0, 0.1)
    yx = np.c_[np.sin(2 * np.pi * x), x]
    layer = Scatter(yx)
    vertices = [[-0.2, -1.4], [0.29, -1.42], [0.29, 11.55], [-0.21, 11.55]]
    expected = [
        0,
        5,
        10,
        15,
        20,
        25,
        30,
        35,
        40,
        45,
        50,
        55,
        60,
        65,
        70,
        75,
        80,
        85,
        90,
        95,
    ]
    indices = layer._get_mask_from_path(vertices, as_indices=True)
    assert indices.ndim == 1
    assert indices.size == 20
    np.testing.assert_equal(indices, expected)

    mask = layer._get_mask_from_path(vertices)
    assert np.sum(mask) == 20
