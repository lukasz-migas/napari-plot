"""Tests for the widgets that plot data from a napari viewer."""

import numpy as np
import pytest
from napari.layers import Labels, Points, Shapes
from npe2 import PluginManifest

import napari_plot
from napari_plot._features_widget import ROW_INDEX, FeaturesPlotWidget
from napari_plot._histogram_widget import HistogramWidget
from napari_plot._layer_sampling import image_plane, resample_path, sample_bilinear
from napari_plot._profile_widget import CursorProfileWidget, LineProfileWidget
from napari_plot._sample_data import make_labeled_blobs, make_spot_time_lapse


def test_sample_bilinear_interpolates_and_masks_outside() -> None:
    """Bilinear sampling is exact on a linear ramp and NaN outside the array."""
    plane = np.add.outer(np.arange(4.0) * 10, np.arange(5.0))
    values = sample_bilinear(plane, [[0, 0], [1.5, 2.25], [3, 4], [-0.1, 0], [0, 4.1]])
    np.testing.assert_allclose(values[:3], [0, 17.25, 34])
    assert np.isnan(values[3:]).all()


def test_resample_path_spacing() -> None:
    """Polylines are resampled at about one step with distances measured along the path."""
    points, distance = resample_path(np.array([[0.0, 0.0], [0.0, 3.0], [4.0, 3.0]]), step=1.0)
    assert distance[-1] == pytest.approx(7)
    np.testing.assert_allclose(np.diff(distance), 7 / (len(distance) - 1))
    np.testing.assert_allclose(points[[0, -1]], [[0, 0], [4, 3]])


def test_image_plane_follows_dims_and_scale(make_napari_viewer) -> None:
    """The displayed plane honors the current step and the layer scale."""
    viewer = make_napari_viewer(strict_qt=False)
    data = np.arange(3 * 4 * 5, dtype=float).reshape(3, 4, 5)
    layer = viewer.add_image(data, scale=(2, 1, 1))
    viewer.dims.set_point(0, 4)
    plane, axes = image_plane(layer, viewer.dims)
    assert axes == [1, 2]
    np.testing.assert_array_equal(plane, data[2])


def test_line_profile_follows_shapes(make_napari_viewer, qtbot) -> None:
    """Line shapes produce one profile per image, and moving the shape updates it."""
    viewer = make_napari_viewer(strict_qt=False)
    data = np.tile(np.arange(20, dtype=float), (10, 1))
    image = viewer.add_image(data, name="ramp")
    shapes = viewer.add_shapes([np.array([[5, 2], [5, 12]])], shape_type="line")
    shapes.add_rectangles(np.array([[0, 0], [2, 2]]))
    widget = LineProfileWidget(viewer)
    qtbot.addWidget(widget)

    assert widget.shapes_layer is shapes
    assert list(widget._series) == ["ramp | shape 0"]
    xy = widget._series["ramp | shape 0"].data
    np.testing.assert_allclose(xy[:, 0], xy[:, 1] - 2)
    assert xy[-1, 0] == pytest.approx(10)

    shapes.data = [np.array([[1, 0], [1, 4]])]
    np.testing.assert_allclose(widget._series["ramp | shape 0"].data[:, 1], [0, 1, 2, 3, 4])

    image.data = data * 2
    np.testing.assert_allclose(widget._series["ramp | shape 0"].data[:, 1], [0, 2, 4, 6, 8])

    viewer.layers.remove(shapes)
    assert widget.shapes_layer is None
    assert not widget._series
    assert len(widget.viewer_plot.layers) == 0


def test_line_profile_uses_selected_images(make_napari_viewer, qtbot) -> None:
    """Selecting image layers limits the profiles to them."""
    viewer = make_napari_viewer(strict_qt=False)
    first = viewer.add_image(np.zeros((10, 10)), name="first")
    viewer.add_image(np.ones((10, 10)), name="second")
    viewer.add_shapes([np.array([[5, 1], [5, 8]])], shape_type="path")
    widget = LineProfileWidget(viewer)
    qtbot.addWidget(widget)
    assert set(widget._series) == {"first | shape 0", "second | shape 0"}

    viewer.layers.selection = {first}
    assert set(widget._series) == {"first | shape 0"}


def test_cursor_profile_tracks_cursor_and_step(make_napari_viewer, qtbot) -> None:
    """The profile along the non-displayed axis matches the pixel under the cursor."""
    viewer = make_napari_viewer(strict_qt=False)
    data = np.random.default_rng(0).random((6, 8, 9))
    viewer.add_image(data, name="stack", scale=(0.5, 1, 1))
    widget = CursorProfileWidget(viewer)
    qtbot.addWidget(widget)

    assert widget.axis == 0
    assert widget.axis_choice.currentText() == "Axis 0"
    viewer.cursor.position = (0, 3, 4)
    xy = widget._series["stack"].data
    np.testing.assert_allclose(xy[:, 0], np.arange(6) * 0.5)
    np.testing.assert_allclose(xy[:, 1], data[:, 3, 4])

    viewer.cursor.position = (0, 30, 4)
    assert not widget._series

    viewer.dims.set_point(0, 1.5)
    assert widget.marker.data[0] == pytest.approx(1.5)

    viewer.dims.ndisplay = 3
    assert widget.axis is None


def test_histogram_linked_to_contrast_limits(make_napari_viewer, qtbot) -> None:
    """The histogram counts the displayed plane and its span tracks the contrast limits both ways."""
    viewer = make_napari_viewer(strict_qt=False)
    data = np.random.default_rng(1).random((3, 16, 16))
    image = viewer.add_image(data, contrast_limits=(0, 1))
    widget = HistogramWidget(viewer)
    qtbot.addWidget(widget)

    assert widget.image_layer is image
    _, counts = widget.histogram()
    assert counts.sum() == 16 * 16

    image.contrast_limits = (0.2, 0.7)
    np.testing.assert_allclose(widget.limits.data[0], (0.2, 0.7))

    widget.limits.data = [[0.6, 0.1]]
    assert image.contrast_limits == pytest.approx((0.1, 0.6))

    widget.log_scale.setChecked(True)
    assert widget.viewer_plot.axis.y_scale == "log"
    assert widget._series[image.name].data[:, 1].min() > 0

    second = viewer.add_image(np.ones((16, 16)) * 5, name="second")
    assert widget.image_layer is second
    viewer.layers.remove(second)
    assert widget.image_layer is None
    assert not widget.limits.visible


def test_features_plot_points_selection_round_trip(make_napari_viewer, qtbot) -> None:
    """Plot selections select points, and point selections highlight markers."""
    viewer = make_napari_viewer(strict_qt=False)
    points = viewer.add_points(
        np.zeros((4, 2)), features={"area": [1.0, 2.0, 3.0, 4.0], "mean": [4.0, 3.0, 2.0, 1.0], "name": list("abcd")}
    )
    widget = FeaturesPlotWidget(viewer)
    qtbot.addWidget(widget)

    assert widget.source_layer is points
    assert [widget.x_choice.itemText(i) for i in range(widget.x_choice.count())] == [ROW_INDEX, "area", "mean"]
    np.testing.assert_allclose(widget.scatter_layer.data, [[4, 1], [3, 2], [2, 3], [1, 4]])

    vertices = np.array([[0.5, 0.5], [0.5, 2.5], [5, 2.5], [5, 0.5]])
    widget.viewer_plot._select_data(vertices)
    assert set(points.selected_data) == {0, 1}

    points.selected_data = {3}
    assert widget.scatter_layer.selected_data == {3}

    widget.y_choice.setCurrentText(ROW_INDEX)
    np.testing.assert_allclose(widget.scatter_layer.data[:, 0], [0, 1, 2, 3])

    points.add([1, 1])
    assert len(widget.scatter_layer.data) == 5


def test_features_plot_labels_and_shapes(make_napari_viewer, qtbot) -> None:
    """Labels map rows through their index column, and Shapes keep row selections."""
    viewer = make_napari_viewer(strict_qt=False)
    labels = viewer.add_labels(np.zeros((5, 5), int), features={"index": [0, 3, 7], "area": [0.0, 2.0, 5.0]})
    widget = FeaturesPlotWidget(viewer)
    qtbot.addWidget(widget)
    assert widget.source_layer is labels

    widget.select_rows([2, 1])
    assert labels.selected_label == 3
    labels.selected_label = 7
    assert widget.scatter_layer.selected_data == {2}

    shapes = viewer.add_shapes([np.array([[0, 0], [1, 1]])] * 2, shape_type="line", features={"length": [1.0, 2.0]})
    assert widget.source_layer is shapes
    widget.select_rows([1])
    assert set(shapes.selected_data) == {1}

    viewer.layers.remove(shapes)
    viewer.layers.selection.active = None
    assert widget.source_layer is None
    assert len(widget.scatter_layer.data) == 0


def test_sample_data_layers() -> None:
    """Sample data returns valid layer tuples with features for the features widget."""
    image, points, shapes = make_spot_time_lapse()
    assert image[0].ndim == 3
    assert image[2] == "image"
    assert points[0].shape[1] == 3
    assert set(points[1]["features"]) >= {"intensity", "speed"}
    assert shapes[2] == "shapes"
    assert isinstance(Points(points[0], **points[1]), Points)
    assert isinstance(Shapes(shapes[0], **shapes[1]), Shapes)

    _, labels = make_labeled_blobs()
    layer = Labels(labels[0], **labels[1])
    assert set(np.unique(labels[0])) - {0} == set(layer.features["index"])


def test_manifest_contributes_menus_and_samples() -> None:
    """Integration widgets are contributed to napari's layer menus and sample data is registered."""
    manifest = PluginManifest.from_file(napari_plot.__path__[0] + "/napari.yaml")
    menus = {menu: [item.command for item in items] for menu, items in manifest.contributions.menus.items()}
    assert "napari_plot.LineProfileWidget" in menus["napari/layers/measure"]
    assert "napari_plot.CursorProfileWidget" in menus["napari/layers/measure"]
    assert "napari_plot.HistogramWidget" in menus["napari/layers/visualize"]
    assert "napari_plot.FeaturesPlotWidget" in menus["napari/layers/visualize"]
    widgets = {widget.command for widget in manifest.contributions.widgets}
    assert {command for items in menus.values() for command in items} <= widgets
    assert {sample.key for sample in manifest.contributions.sample_data} == {"spot_time_lapse", "labeled_blobs"}


def test_open_sample_through_napari(make_napari_viewer) -> None:
    """napari can open the contributed sample when the plugin is installed."""
    from napari.plugins import _initialize_plugins
    from npe2 import PluginManager

    _initialize_plugins()
    if "napari_plot" not in PluginManager.instance()._manifests:
        pytest.skip("napari_plot is not installed as a plugin in this environment")
    viewer = make_napari_viewer(strict_qt=False)
    viewer.open_sample("napari_plot", "labeled_blobs")
    assert [layer.name for layer in viewer.layers] == ["Blobs", "Blob labels"]
