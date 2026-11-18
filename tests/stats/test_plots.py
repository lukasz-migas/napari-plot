"""Each statistical plot builds the expected layers on a ViewerModel."""

import inspect

import numpy as np
import pandas as pd
import pytest

from napari_plot import stats
from napari_plot.components.viewer_model import ViewerModel
from napari_plot.layers import Areas, Bar, ErrorBar, MultiLine, Scatter, Text


@pytest.fixture
def tips() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    n = 120
    return pd.DataFrame(
        {
            "day": rng.choice(["Thu", "Fri", "Sat"], n),
            "smoker": rng.choice(["Yes", "No"], n),
            "size": rng.integers(1, 5, n),
            "bill": rng.gamma(4, 5, n),
            "tip": rng.gamma(2, 1.5, n),
        }
    )


def _types(layers: list) -> list[str]:
    return [type(layer).__name__ for layer in layers]


def test_viewer_methods_mirror_stats_functions() -> None:
    for name in stats.__all__:
        method = getattr(ViewerModel, name)
        function = getattr(stats, name)
        assert method.__doc__ == function.__doc__
        assert list(inspect.signature(method).parameters)[1:] == list(inspect.signature(function).parameters)[1:]


def test_boxplot_with_hue(tips: pd.DataFrame) -> None:
    viewer = ViewerModel()
    layers = viewer.boxplot(tips, x="day", y="bill", hue="smoker", order=["Thu", "Fri", "Sat"])
    boxes = [layer for layer in layers if isinstance(layer, Bar)]
    assert len(boxes) == 2
    assert boxes[0].data.shape == (3, 4)  # position, q3, q1, width
    np.testing.assert_allclose(boxes[0].positions, [-0.2, 0.8, 1.8])
    assert viewer.axis.x_categories == ("Thu", "Fri", "Sat")
    assert viewer.axis.x_label == "day"
    assert viewer.axis.y_label == "bill"
    assert [entry.label for entry in viewer.legend.entries] == list(pd.unique(tips["smoker"]))
    assert all(isinstance(layer, MultiLine) for layer in layers if "lines" in layer.name)


def test_horizontal_boxplot_swaps_axes(tips: pd.DataFrame) -> None:
    viewer = ViewerModel()
    layers = viewer.boxplot(tips, x="bill", y="day", showfliers=False)
    assert _types(layers) == ["Bar", "MultiLine"]
    assert layers[0].orientation == "horizontal"
    assert viewer.axis.y_categories is not None
    assert viewer.axis.x_categories is None


def test_boxenplot_levels(tips: pd.DataFrame) -> None:
    layers = ViewerModel().boxenplot(tips, x="day", y="bill")
    boxes = layers[0]
    assert isinstance(boxes, Bar)
    assert len(boxes.data) > 3
    assert np.all(boxes.widths <= 0.8 + 1e-9)


@pytest.mark.parametrize("inner", ["box", "quart", "stick", "point", None])
def test_violinplot_inner_variants(tips: pd.DataFrame, inner: str | None) -> None:
    layers = ViewerModel().violinplot(tips, x="day", y="bill", inner=inner)
    bodies = layers[0]
    assert isinstance(bodies, Areas)
    assert len(bodies.data) == 3
    assert bodies.orientation == "horizontal"  # density spreads along x for vertical violins


def test_split_violin_halves_meet_at_center(tips: pd.DataFrame) -> None:
    layers = ViewerModel().violinplot(tips, x="day", y="bill", hue="smoker", split=True, inner=None, order=["Thu"])
    left, right = layers[0].data
    np.testing.assert_allclose(left[:, 2], 0)
    np.testing.assert_allclose(right[:, 1], 0)


def test_barplot_estimates_and_errors(tips: pd.DataFrame) -> None:
    viewer = ViewerModel()
    layers = viewer.barplot(tips, x="day", y="bill", hue="smoker", seed=0, n_boot=100)
    assert _types(layers) == ["Bar", "Bar", "ErrorBar"]
    error = layers[-1]
    assert isinstance(error, ErrorBar)
    assert len(error.data) == 6
    no_errors = ViewerModel().barplot(tips, x="day", y="bill", errorbar=None, estimator="median")
    assert _types(no_errors) == ["Bar"]
    np.testing.assert_allclose(sorted(no_errors[0].values), sorted(tips.groupby("day")["bill"].median().to_numpy()))


def test_strip_and_swarm_plot_every_observation(tips: pd.DataFrame) -> None:
    strip = ViewerModel().stripplot(tips, x="day", y="bill", hue="smoker", dodge=True, seed=0)
    assert _types(strip) == ["Scatter", "Scatter"]
    assert sum(len(layer.data) for layer in strip) == len(tips)
    swarm = ViewerModel().swarmplot(tips, x="day", y="bill")
    assert isinstance(swarm[0], Scatter)
    assert len(swarm[0].data) == len(tips)
    assert swarm[0].scaling is False


def test_kdeplot_and_histplot(tips: pd.DataFrame) -> None:
    kde = ViewerModel().kdeplot(tips, x="bill", hue="smoker", fill=True)
    assert _types(kde) == ["Areas", "MultiLine"]
    horizontal = ViewerModel().kdeplot(y=tips["bill"])
    assert _types(horizontal) == ["MultiLine"]

    hist = ViewerModel().histplot(tips, x="bill", hue="smoker", multiple="stack", bins=8, kde=True)
    assert _types(hist) == ["Bar", "Bar", "MultiLine"]
    np.testing.assert_allclose(hist[1].baselines, hist[0].values)
    filled = ViewerModel().histplot(tips, x="bill", hue="smoker", multiple="fill", bins=8)
    np.testing.assert_allclose(filled[1].values[filled[1].values > 0], 1)
    with pytest.raises(ValueError, match="multiple"):
        ViewerModel().histplot(tips, x="bill", multiple="overlap")


def test_distplot_components(tips: pd.DataFrame) -> None:
    layers = ViewerModel().distplot(tips["bill"].to_numpy(), rug=True)
    assert _types(layers) == ["Bar", "MultiLine", "MultiLine"]
    assert len(layers[-1].data["ys"]) == len(tips)  # one rug tick per observation


def test_heatmap_orientation_and_annotations() -> None:
    viewer = ViewerModel()
    matrix = pd.DataFrame([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], index=list("abc"), columns=["x", "y"])
    image, text = viewer.heatmap(matrix, annot=True, fmt=".0f")
    np.testing.assert_array_equal(image.data[-1], [1.0, 2.0])  # first row drawn at the top
    assert viewer.axis.y_categories == ("c", "b", "a")
    assert isinstance(text, Text)
    assert list(text.text[:2]) == ["1", "2"]
    np.testing.assert_array_equal(text.data[0], [0, 2])
    masked = ViewerModel().heatmap(np.ones((2, 2)), annot=True, mask=np.eye(2, dtype=bool))
    assert len(masked[1].data) == 2


def test_clustermap_reorders_and_draws_dendrograms() -> None:
    rng = np.random.default_rng(1)
    matrix = np.vstack((rng.normal(0, 0.1, (3, 4)), rng.normal(5, 0.1, (3, 4))))[[0, 3, 1, 4, 2, 5]]
    layers = ViewerModel().clustermap(matrix)
    image, tree = layers
    groups = np.round(image.data[:, 0] / 5).tolist()
    assert groups in ([0, 0, 0, 1, 1, 1], [1, 1, 1, 0, 0, 0])  # clustered rows end up adjacent
    assert isinstance(tree, MultiLine)
    assert len(tree.data["ys"]) == 5 + 3
    with pytest.raises(ValueError, match="z_score"):
        ViewerModel().clustermap(matrix, z_score=0, standard_scale=0)


def test_scatterplot_semantics(tips: pd.DataFrame) -> None:
    viewer = ViewerModel()
    (layer,) = viewer.scatterplot(tips, x="bill", y="tip", hue="day", size="size", style="smoker")
    assert isinstance(layer, Scatter)
    np.testing.assert_array_equal(layer.data[:, 1], tips["bill"])  # Scatter stores (y, x)
    assert len(np.unique(layer.size)) == tips["size"].nunique()
    assert set(layer.symbol) == {"disc", "x"}
    assert len(viewer.legend.entries) == 3 + 2
    numeric = ViewerModel().scatterplot(tips, x="bill", y="tip", hue="tip")
    assert len(np.unique(numeric[0].face_color, axis=0)) > 10


def test_lineplot_aggregates_with_band(tips: pd.DataFrame) -> None:
    layers = ViewerModel().lineplot(tips, x="size", y="tip", hue="smoker", seed=0, n_boot=100)
    assert _types(layers) == ["Areas", "MultiLine"]
    assert len(layers[1].data["ys"]) == 2  # one line per hue level
    assert len(layers[0].data) == 2  # one error band per hue level
    bars = ViewerModel().lineplot(tips, x="size", y="tip", err_style="bars", errorbar="sd")
    assert _types(bars) == ["ErrorBar", "MultiLine"]
    raw = ViewerModel().lineplot(tips, x="bill", y="tip", estimator=None)
    assert _types(raw) == ["MultiLine"]


def test_relplot_dispatch(tips: pd.DataFrame) -> None:
    assert _types(ViewerModel().relplot(tips, x="bill", y="tip", hue="day")) == ["Scatter"]
    assert _types(ViewerModel().relplot(tips, x="size", y="tip", kind="line", errorbar=None)) == ["MultiLine"]
    with pytest.raises(ValueError, match="kind"):
        ViewerModel().relplot(tips, x="bill", y="tip", kind="bar")
    with pytest.raises(ValueError, match="size and style"):
        ViewerModel().relplot(tips, x="bill", y="tip", size="size", kind="line")
