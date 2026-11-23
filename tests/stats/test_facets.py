"""Figure-level statistical plots use the viewer's per-cell axes."""

import pandas as pd

from napari_plot import JointGrid
from napari_plot.components.viewer_model import ViewerModel
from napari_plot.stats.facets import FacetGrid, catplot, displot, jointplot, lmplot, pairplot


def test_distribution_facets_keep_row_and_column_positions() -> None:
    viewer = ViewerModel()
    data = pd.DataFrame({"x": [1, 2, 3], "row": ["A", "A", "B"], "col": ["L", "L", "R"]})
    result = displot(viewer, data, x="x", row="row", col="col", facet_kws={"sharey": False})
    grid = viewer.canvas.grid

    assert isinstance(result, FacetGrid)
    assert result.layers == list(viewer.layers)
    assert grid.enabled
    assert grid.sharex
    assert not grid.sharey
    assert list(grid.iter_viewboxes(viewer.layers)) == [((0, 0), (0,)), ((0, 1), ()), ((1, 0), ()), ((1, 1), (1,))]
    assert "row = B" in grid.cell(1, 1).x_label
    assert all(layer.name_overlay is not None for layer in viewer.layers)


def test_categorical_facets_share_category_positions() -> None:
    viewer = ViewerModel()
    data = pd.DataFrame({"species": ["a", "b", "a"], "site": ["North", "South", "North"]})
    plot = catplot(viewer, data, x="species", col="site", kind="count")
    grid = viewer.canvas.grid

    assert len(plot.layers) == 2
    assert grid.cell(0, 0).x_categories == grid.cell(0, 1).x_categories == ("a", "b")
    assert grid.cell(0, 0).y_label == "Count"


def test_lmplot_splits_regressions_by_facet_and_hue() -> None:
    viewer = ViewerModel()
    data = pd.DataFrame({"x": [1, 2, 1, 2], "y": [2, 4, 3, 6], "site": ["A", "A", "B", "B"]})
    result = lmplot(viewer, data, x="x", y="y", hue="site", col="site", ci=None)

    assert len(result.layers) == 4
    assert [entry.label for entry in viewer.legend.entries] == ["A", "B"]
    assert list(viewer.canvas.grid.iter_viewboxes(viewer.layers)) == [((0, 0), (0, 1)), ((0, 1), (2, 3))]


def test_pairplot_and_jointplot_create_labeled_panels() -> None:
    data = pd.DataFrame({"a": [1, 2, 3, 4], "b": [10, 30, 20, 60]})
    viewer = ViewerModel()
    pair = pairplot(viewer, data, corner=True)
    grid = viewer.canvas.grid
    assert len(pair.layers) == 3
    assert grid.cell(0, 0).x_label == "a"
    assert grid.cell(1, 0).y_label == "b"

    viewer.reset_plot()
    joint = jointplot(viewer, data, x="a", y="b")
    assert isinstance(joint, JointGrid)
    assert len(joint.layers) == 3
    assert grid.joint
    assert dict(grid.iter_viewboxes(viewer.layers))[(1, 0)] == (1,)


def test_jointplot_accepts_an_empty_frame() -> None:
    viewer = ViewerModel()
    joint = viewer.jointplot(pd.DataFrame({"x": [], "y": []}), x="x", y="y")

    assert joint.layers == []
    assert viewer.canvas.grid.joint
