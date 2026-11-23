"""Regression and distribution plots introduced by the extended stats API."""

import numpy as np
import pandas as pd

from napari_plot.components.viewer_model import ViewerModel
from napari_plot.layers import Areas, Bar, MultiLine, Scatter


def test_ecdf_steps_include_ties() -> None:
    viewer = ViewerModel()
    (curve,) = viewer.ecdfplot([1, 1, 3], stat="count")
    np.testing.assert_array_equal(curve.data["xs"][0], [1, 1, 3, 3])
    np.testing.assert_array_equal(curve.data["ys"][0], [0, 2, 2, 3])


def test_histogram_elements_and_bivariate_counts() -> None:
    viewer = ViewerModel()
    fill, line = viewer.histplot([1, 2, 2, 3], bins=[0, 2, 4], element="step")
    assert isinstance(fill, Areas)
    assert isinstance(line, MultiLine)
    (bar,) = viewer.histplot([1, 2, 2, 3], bins=2, fill=False)
    assert isinstance(bar, Bar)
    assert np.all(bar.fill_color[:, 3] == 0)
    (heatmap,) = viewer.histplot(x=[1, 2, 1, 2], y=[2, 2, 5, 5], bins=2)
    np.testing.assert_array_equal(heatmap.data, [[1, 1], [1, 1]])


def test_kde_multiple_fill_and_bivariate() -> None:
    viewer = ViewerModel()
    data = pd.DataFrame({"x": [1, 2, 3, 2, 3, 4], "label": ["a"] * 3 + ["b"] * 3})
    (areas, _) = viewer.kdeplot(data, x="x", hue="label", multiple="fill", fill=True, gridsize=16)
    np.testing.assert_allclose(areas.data[-1][:, 2], 1)
    (density,) = viewer.kdeplot(x=[1, 2, 1, 2, 3], y=[1, 1, 2, 2, 1], gridsize=16)
    assert density.data.shape == (16, 16)
    assert np.all(density.data >= 0)


def test_count_point_regression_and_scatter_group() -> None:
    viewer = ViewerModel()
    data = pd.DataFrame({"category": ["a", "a", "b"], "value": [1, 3, 5]})
    (bars,) = viewer.countplot(data, x="category", stat="percent")
    np.testing.assert_allclose(bars.data[:, 1], [200 / 3, 100 / 3])
    _, points = viewer.pointplot(data, x="category", y="value", errorbar=None)
    assert isinstance(points, Scatter)
    np.testing.assert_allclose(points.data, [[2, 0], [5, 1]])
    viewer.reset_plot()
    line, points = viewer.regplot(x=[1, 2, 3], y=[3, 5, 7], ci=None, group="regression")
    np.testing.assert_allclose(line.data[:, 1], 1 + 2 * line.data[:, 0])
    assert points.metadata["napari_plot.group"] == "regression"
    (layer,) = viewer.scatterplot(x=[1, 2], y=[3, 4], group="example")
    assert layer.metadata["napari_plot.group"] == "example"


def test_lineplot_maps_style_and_size_to_layers() -> None:
    viewer = ViewerModel()
    data = pd.DataFrame(
        {
            "x": [0, 1, 0, 1],
            "y": [1, 2, 3, 4],
            "method": ["a", "a", "b", "b"],
            "width": [1, 1, 3, 3],
        }
    )
    first, first_markers, second, second_markers = viewer.lineplot(
        data,
        x="x",
        y="y",
        style="method",
        size="width",
        sizes=(1, 3),
        markers=True,
        dashes={"a": (), "b": (4, 2)},
        errorbar=None,
    )
    assert (first.width, second.width) == (1, 3)
    assert first.dashes is None
    assert second.dashes == (4, 2)
    assert first_markers.symbol[0] != second_markers.symbol[0]
    assert len({layer.metadata["napari_plot.group"] for layer in viewer.layers}) == 1


def test_scatterplot_accepts_a_palette_keyed_by_hue() -> None:
    viewer = ViewerModel()
    (points,) = viewer.scatterplot(
        x=[0, 1, 2],
        y=[3, 4, 5],
        hue=["Control", "Treated", "Control"],
        palette={"Control": "red", "Treated": "blue"},
    )
    np.testing.assert_allclose(points.face_color, [[1, 0, 0, 1], [0, 0, 1, 1], [1, 0, 0, 1]])
