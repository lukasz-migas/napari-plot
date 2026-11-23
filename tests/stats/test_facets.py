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


def test_pairgrid_regions_and_repeated_mapping() -> None:
    from napari_plot.stats import PairGrid

    viewer = ViewerModel()
    data = pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})
    grid = PairGrid(viewer, data, x_vars=["b", "a", "c"], y_vars=["a", "c"])
    calls = []

    def callback(stage: ViewerModel, *, data: pd.DataFrame, x: str, y: str | None = None) -> None:
        calls.append((x, y))
        stage.add_line([[0, 0], [1, 1]])

    assert not viewer.canvas.grid.enabled
    assert grid.map_diag(callback).map_offdiag(callback) is grid
    assert calls == [("a", None), ("c", None), ("b", "a"), ("c", "a"), ("b", "c"), ("a", "c")]
    assert len(grid.layers) == 6
    grid.map_upper(callback)
    assert calls[-1] == ("c", "a")
    assert len(grid.layers) == 7
    grid.map_lower(callback)
    assert calls[-1] == ("b", "c")
    assert len(grid.layers) == 8
    assert viewer.canvas.grid.cell(1, 0).x_label == "b"
    assert viewer.canvas.grid.cell(1, 0).y_label == "c"


def test_pairgrid_failure_is_atomic_and_corner_works() -> None:
    import pytest

    from napari_plot.stats import PairGrid

    viewer = ViewerModel()
    grid = PairGrid(viewer, pd.DataFrame({"a": [1, 2], "b": [3, 4]}), corner=True)
    calls = []

    def callback(stage: ViewerModel, *, data: pd.DataFrame, x: str, y: str) -> None:
        calls.append((x, y))
        if len(calls) == 2:
            raise RuntimeError("failed")
        stage.add_line([[0, 0], [1, 1]])

    with pytest.raises(RuntimeError, match="failed"):
        grid.map(callback)
    assert len(viewer.layers) == 0
    assert not viewer.canvas.grid.enabled
    assert grid.layers == []
    with pytest.raises(ValueError, match="Unknown column"):
        PairGrid(viewer, grid.data, x_vars=["missing"])
    assert not viewer.canvas.grid.enabled


def test_pairgrid_hue_and_opt_out() -> None:
    from napari_plot.stats import PairGrid, histplot, regplot, scatterplot

    data = pd.DataFrame({"a": [1, 2, 3, 4], "b": [2, 4, 3, 5], "group": ["B", "A", "B", "A"]})
    viewer = ViewerModel()
    grid = PairGrid(viewer, data, hue="group")
    grid.map_offdiag(scatterplot).map_diag(histplot)
    assert [entry.label for entry in viewer.legend.entries] == ["B", "A"]
    assert viewer.canvas.grid.cell(0, 0).y_label == "Count"
    grid.map_lower(regplot, hue=None, ci=None)
    assert len(grid.layers) > 4


def test_pairgrid_failure_preserves_existing_mapping() -> None:
    import pytest

    from napari_plot.stats import PairGrid, histplot

    viewer = ViewerModel()
    grid = PairGrid(viewer, pd.DataFrame({"a": [1, 2], "b": [3, 4]})).map_diag(histplot)
    old_layers = list(viewer.layers)
    old_cells = tuple(cell.model_dump() for cell in viewer.canvas.grid.cells)
    count = 0

    def fail(stage: ViewerModel, *, data: pd.DataFrame, x: str, y: str) -> None:
        nonlocal count
        count += 1
        if count == 2:
            raise ValueError("failed")
        stage.add_line([[0, 0], [1, 1]])

    with pytest.raises(ValueError, match="failed"):
        grid.map_offdiag(fail)
    assert list(viewer.layers) == old_layers
    assert grid.layers == old_layers
    assert tuple(cell.model_dump() for cell in viewer.canvas.grid.cells) == old_cells


def test_pairgrid_hue_order_uses_full_data_with_missing_values() -> None:
    from napari_plot.stats import PairGrid, histplot

    data = pd.DataFrame(
        {
            "a": [1.0, 2.0, float("nan"), float("nan")],
            "b": [3.0, float("nan"), 3.0, 4.0],
            "group": ["A", "A", "B", "B"],
        }
    )
    viewer = ViewerModel()
    grid = PairGrid(viewer, data, hue="group").map_diag(histplot)
    assert [entry.label for entry in viewer.legend.entries] == ["A", "B"]
    assert len(grid.layers) >= 2

    viewer = ViewerModel()
    wrapped = pairplot(viewer, data, hue="group")
    wrapped.map_diag(histplot)
    assert [entry.label for entry in viewer.legend.entries] == ["A", "B"]
