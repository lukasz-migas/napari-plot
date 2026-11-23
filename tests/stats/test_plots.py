"""Each statistical plot builds the expected layers on a ViewerModel."""

import inspect
from typing import Any
from uuid import UUID

import numpy as np
import pandas as pd
import pytest

from napari_plot import stats
from napari_plot.components.viewer_model import ViewerModel
from napari_plot.layers import Areas, Bar, ErrorBar, MultiLine, Scatter, Text
from napari_plot.layers._grouping import LAYER_GROUP_KEY


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


@pytest.mark.parametrize(
    ("plot", "options"),
    [
        ("boxplot", {"x": "day", "y": "bill", "hue": "smoker"}),
        ("boxenplot", {"x": "day", "y": "bill", "hue": "smoker"}),
        ("barplot", {"x": "day", "y": "bill", "hue": "smoker", "errorbar": "sd"}),
        ("stripplot", {"x": "day", "y": "bill", "hue": "smoker"}),
        ("swarmplot", {"x": "day", "y": "bill", "hue": "smoker"}),
        ("kdeplot", {"x": "bill", "hue": "smoker", "fill": True}),
        ("histplot", {"x": "bill", "hue": "smoker", "kde": True}),
        ("rugplot", {"x": "bill", "y": "tip"}),
        ("distplot", {"rug": True, "hist_kws": {"group": "nested hist"}}),
        ("heatmap", {"annot": True}),
        ("clustermap", {"annot": True}),
        ("lineplot", {"x": "size", "y": "bill", "errorbar": "sd", "err_style": "bars"}),
        ("relplot", {"kind": "line", "x": "size", "y": "bill", "errorbar": "sd"}),
    ],
)
def test_compound_plot_group_is_shared_at_insertion(tips: pd.DataFrame, plot: str, options: dict[str, Any]) -> None:
    viewer = ViewerModel()
    inserted_groups: list[str | None] = []
    viewer.layers.events.inserted.connect(
        lambda event: inserted_groups.append(event.value.metadata.get(LAYER_GROUP_KEY))
    )
    if plot == "distplot":
        data = tips["bill"].to_numpy()
    elif plot in {"heatmap", "clustermap"}:
        data = tips[["bill", "tip"]].head(5)
    else:
        data = tips
    draw = getattr(viewer, plot)

    first = draw(data, name="same name", **options)
    second = draw(data, name="same name", **options)
    shared = draw(data, group="shared", **options)

    assert len(first) == len(second) == len(shared) > 1
    first_id = first[0].metadata[LAYER_GROUP_KEY]
    second_id = second[0].metadata[LAYER_GROUP_KEY]
    assert UUID(first_id).version == UUID(second_id).version == 4
    assert first_id != second_id
    assert inserted_groups == [first_id] * len(first) + [second_id] * len(second) + ["shared"] * len(shared)
    assert [layer.metadata[LAYER_GROUP_KEY] for layer in [*first, *second, *shared]] == inserted_groups


def test_grouping_with_only_one_layer(tips: pd.DataFrame) -> None:
    viewer = ViewerModel()
    (density,) = viewer.kdeplot(tips, x="bill", group=None)
    (scatter,) = viewer.scatterplot(tips, x="bill", y="tip")
    assert UUID(density.metadata[LAYER_GROUP_KEY]).version == 4
    assert LAYER_GROUP_KEY not in scatter.metadata


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
    group = bodies.metadata["napari_plot.group"]
    assert isinstance(group, str)
    assert all(layer.metadata["napari_plot.group"] == group for layer in layers)


def test_violinplot_group_ids_and_insertions(tips: pd.DataFrame) -> None:
    viewer = ViewerModel()
    inserted_groups: list[str | None] = []
    viewer.layers.events.inserted.connect(
        lambda event: inserted_groups.append(event.value.metadata.get("napari_plot.group"))
    )

    first = viewer.violinplot(tips, x="day", y="bill", name="same")
    second = viewer.violinplot(tips, x="day", y="bill", name="same")
    first_id = first[0].metadata["napari_plot.group"]
    second_id = second[0].metadata["napari_plot.group"]
    assert first_id != second_id
    assert inserted_groups == [first_id] * len(first) + [second_id] * len(second)
    inserted_groups.clear()

    shared = "shared group"
    third = viewer.violinplot(tips, x="day", y="bill", group=shared)
    fourth = stats.violinplot(viewer, tips, x="day", y="bill", group=shared)
    native = viewer.add_image(np.zeros((2, 2)), metadata={"napari_plot.group": shared})
    assert all(layer.metadata["napari_plot.group"] == shared for layer in [*third, *fourth, native])
    assert inserted_groups == [shared] * (len(third) + len(fourth) + 1)


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


@pytest.mark.parametrize("dodge", [False, True])
def test_swarmplot_separates_overlapping_hues(dodge: bool) -> None:
    viewer = ViewerModel()
    red, blue = viewer.swarmplot(x=[1, 1, 1, 1], y=["A"] * 4, hue=["red", "blue"] * 2, dodge=dodge)
    points = np.vstack((red.data, blue.data))
    np.testing.assert_array_equal(points[:, 1], np.ones(4))
    assert len(np.unique(points[:, 0])) == 4
    assert viewer.axis.y_categories == ("A",)
    if dodge:
        assert np.all(red.data[:, 0] < 0)
        assert np.all(blue.data[:, 0] > 0)


def test_swarmplot_warns_when_points_hit_gutters() -> None:
    with pytest.warns(UserWarning, match="points cannot be placed"):
        (layer,) = ViewerModel().swarmplot(y=[1, 1, 1], width=0.001)
    assert np.all(np.abs(layer.data[:, 1]) <= 0.0005)


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


def test_rugplot_marks_both_margins_with_hue() -> None:
    viewer = ViewerModel()
    data = pd.DataFrame({"bill": [1.0, 2.0, np.nan], "tip": [4.0, 5.0, 6.0], "group": ["A", "B", "A"]})
    x_rug, y_rug = viewer.rugplot(
        data, x="bill", y="tip", hue="group", palette={"A": "red", "B": "blue"}, hue_order=["B", "A"], height=0.1
    )
    assert _types([x_rug, y_rug]) == ["MultiLine", "MultiLine"]
    xmin, xmax, ymin, ymax = viewer.camera.rect
    np.testing.assert_array_equal(x_rug.data["xs"], [[1, 1], [2, 2]])
    np.testing.assert_array_equal(y_rug.data["ys"], [[4, 4], [5, 5]])
    np.testing.assert_allclose(x_rug.data["ys"], [[ymin, ymin + 0.1 * (ymax - ymin)]] * 2)
    np.testing.assert_allclose(y_rug.data["xs"], [[xmin, xmin + 0.1 * (xmax - xmin)]] * 2)
    np.testing.assert_allclose(x_rug.color, [[1, 0, 0, 1], [0, 0, 1, 1]])
    assert (viewer.axis.x_label, viewer.axis.y_label) == ("bill", "tip")
    assert [entry.label for entry in viewer.legend.entries] == ["B", "A"]


def test_rugplot_expands_margin_on_existing_plot() -> None:
    baselines = []
    for expand_margins in (False, True):
        viewer = ViewerModel()
        viewer.plot([1, 2], [10, 20])
        viewer.axis.y_label = "Density"
        (rug,) = viewer.rugplot([1, 2], expand_margins=expand_margins, color="red", linewidth=2)
        assert viewer.axis.y_label == "Density"
        assert rug.width == 2
        np.testing.assert_array_equal(rug.data["xs"], [[1, 1], [2, 2]])
        baselines.append(rug.data["ys"][0][0])
    assert baselines[1] < baselines[0]
    assert ViewerModel().rugplot(x=[np.nan]) == []


def test_rugplot_preserves_axis_coordinates() -> None:
    viewer = ViewerModel()
    viewer.axis.x_scale = "log"
    viewer.axis.y_categories = ("A", "B")
    x_rug, y_rug = viewer.rugplot(x=[1, 10, 100], y=["B", "A", "C"])
    assert viewer.axis.y_categories == ("A", "B", "C")
    xmin, xmax, ymin, ymax = viewer.camera.rect
    assert 0 < xmin < 1 < 100 < xmax
    assert ymin < 0 < 2 < ymax
    np.testing.assert_array_equal(x_rug.data["xs"], [[1, 1], [10, 10], [100, 100]])
    np.testing.assert_array_equal(y_rug.data["ys"], [[1, 1], [0, 0], [2, 2]])


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


@pytest.mark.parametrize("plot", ["boxplot", "boxenplot", "violinplot", "barplot"])
def test_categorical_layers_describe_their_groups(tips: pd.DataFrame, plot: str) -> None:
    viewer = ViewerModel()
    layers = getattr(viewer, plot)(tips, x="day", y="bill", hue="smoker", order=["Thu", "Fri", "Sat"])
    picked = [layer for layer in layers if "groups" in layer.metadata]
    assert picked
    for layer in picked:
        groups = layer.metadata["groups"]
        count = len(layer.data)
        assert len(groups) == count
    group = picked[0].metadata["groups"][0]
    assert set(group) == {"category", "hue", "n", "median", "q1", "q3"}
    values = tips.loc[(tips["day"] == group["category"]) & (tips["smoker"] == group["hue"]), "bill"]
    assert group["n"] == len(values)
    assert group["median"] == pytest.approx(values.median())


def test_violin_hover_finds_group(tips: pd.DataFrame) -> None:
    viewer = ViewerModel()
    layers = viewer.violinplot(tips, x="day", y="bill", order=["Thu", "Fri", "Sat"])
    bodies = layers[0]
    median = bodies.metadata["groups"][1]["median"]
    index = bodies.get_value((median, 1.0))
    assert bodies.metadata["groups"][index]["category"] == "Fri"


def test_strip_points_carry_category_feature(tips: pd.DataFrame) -> None:
    viewer = ViewerModel()
    layers = viewer.stripplot(tips, x="day", y="bill", hue="smoker", order=["Thu", "Fri", "Sat"], linewidth=1)
    for layer in layers:
        assert len(layer.features["category"]) == len(layer.data)
        assert set(layer.features["category"]) <= {"Thu", "Fri", "Sat"}
        assert layer.features["hue"].nunique() == 1
        np.testing.assert_allclose(layer.border_width, 1)


def test_saturation_desaturates_fill_and_legend(tips: pd.DataFrame) -> None:
    viewer = ViewerModel()
    full = viewer.boxplot(
        tips, x="day", y="bill", hue="smoker", palette={"Yes": "red", "No": "blue"}, hue_order=["No", "Yes"]
    )[0]
    np.testing.assert_allclose(full.fill_color[0], [0, 0, 1, 1])
    muted = viewer.boxplot(
        tips,
        x="day",
        y="bill",
        hue="smoker",
        palette={"Yes": "red", "No": "blue"},
        hue_order=["No", "Yes"],
        saturation=0.5,
    )
    muted = muted[0]
    assert not np.allclose(muted.fill_color[0], [0, 0, 1, 1])
    assert muted.fill_color[0][2] > muted.fill_color[0][0] > 0


def test_reset_plot_clears_categories_scale_and_legend(tips: pd.DataFrame) -> None:
    viewer = ViewerModel()
    viewer.boxplot(tips, x="day", y="bill", hue="smoker")
    viewer.axis.y_scale = "log"
    viewer.camera.x_range = (-1, 5)
    viewer.camera.y_range = (1, 50)
    viewer.axis.x_tick_rotation = 45
    viewer.axis.x_thin_categories = False
    viewer.reset_plot()
    assert len(viewer.layers) == 0
    assert viewer.camera.x_range is None
    assert viewer.camera.y_range is None
    assert viewer.axis.x_categories is None
    assert viewer.axis.x_tick_rotation == 0
    assert viewer.axis.x_thin_categories
    assert viewer.axis.y_scale == "linear"
    assert not viewer.legend.visible
