"""Every seaborn symbol reused by napari-plot still behaves as the adapter expects."""

import numpy as np
import pandas as pd

from napari_plot.stats import _seaborn as sb


def test_palette_helpers() -> None:
    assert len(sb.color_palette("deep", n_colors=3)) == 3
    assert sb.light_palette((0.2, 0.4, 0.6), as_cmap=True)(0.5).__len__() == 4
    assert list(sb.categorical_order(pd.Series(["b", "a", "b"]))) == ["b", "a"]
    assert sb.relative_luminance((1, 1, 1)) == 1


def test_statistics_classes() -> None:
    values = np.random.default_rng(0).normal(size=200)
    density, support = sb.KDE(gridsize=50)(values)
    assert density.shape == support.shape == (50,)

    histogram = sb.Histogram(stat="count", bins=5)
    heights, edges = histogram(values)
    assert heights.sum() == 200
    assert len(edges) == 6
    assert "bins" in histogram.define_bin_params(values)

    result = sb.EstimateAggregator("mean", ("ci", 95), n_boot=50, seed=0)(pd.DataFrame({"v": values}), "v")
    assert {"v", "vmin", "vmax"} <= set(result.index)

    letters = sb.LetterValues("tukey", 0.007, 0.05)(values)
    assert {"k", "levels", "values", "fliers", "median"} <= set(letters)


def test_beeswarm_core_works_on_arrays() -> None:
    xyr = np.column_stack((np.zeros(5), np.zeros(5), np.ones(5)))
    swarm = sb.Beeswarm().beeswarm(xyr)
    assert swarm.shape == (5, 3)
    assert len(np.unique(swarm[:, 0])) == 5


def test_matrix_helpers_construct_without_axes() -> None:
    frame = pd.DataFrame(np.arange(12.0).reshape(3, 4))
    mapper = sb._HeatMapper(frame, None, None, None, None, False, True, ".1f", None, False, None)
    assert (mapper.vmin, mapper.vmax) == (0, 11)
    assert mapper.annot
    assert mapper.plot_data.shape == (3, 4)

    tree = sb._DendrogramPlotter(frame, None, "euclidean", "average", 0, False, True)
    assert sorted(tree.reordered_ind) == [0, 1, 2]
    assert np.asarray(tree.independent_coord).shape[1] == 4
    assert sb.ClusterGrid.z_score(frame, 1).shape == frame.shape
    assert sb.ClusterGrid.standard_scale(frame, 0).shape == frame.shape
