"""Distribution plots: kernel density, histogram and the combined distplot."""

from __future__ import annotations

import typing as ty
from collections.abc import Mapping

import numpy as np
import pandas as pd

from napari_plot.stats import _common as cm
from napari_plot.stats._data import Orient, long_frame
from napari_plot.stats._estimators import histogram, histogram_bins, kde
from napari_plot.stats._palette import level_colors

if ty.TYPE_CHECKING:
    from napari.layers import Layer

    from napari_plot.components.viewer_model import ViewerModel

_NORMALIZED_STATS = {"density", "probability", "proportion", "percent"}


class _Distribution(ty.NamedTuple):
    """Observations split by hue level."""

    groups: dict[ty.Any, np.ndarray]
    orient: Orient
    label: str | None
    hue_label: str | None
    has_hue: bool

    @property
    def total(self) -> int:
        return sum(len(values) for values in self.groups.values())

    @property
    def all_values(self) -> np.ndarray:
        return np.concatenate(list(self.groups.values())) if self.groups else np.empty(0)


def _distribution(data: ty.Any, x: ty.Any, y: ty.Any, hue: ty.Any, hue_order: list | None) -> _Distribution:
    """Collect univariate observations (along ``x`` or ``y``) grouped by hue level."""
    from napari_plot.stats._seaborn import categorical_order

    if x is None and y is None:
        if isinstance(data, (pd.DataFrame, Mapping)):  # wide form: each column is a hue level
            frame = pd.DataFrame({k: pd.Series(np.asarray(v)) for k, v in dict(data).items()})
            frame = frame.select_dtypes("number").melt(var_name="hue", value_name="x").dropna()
            frame, labels = long_frame(frame, x="x", hue="hue")
            labels["hue"] = None
        else:
            frame, labels = long_frame(None, x=np.asarray(data, dtype=float).ravel(), dropna=("x",))
    else:
        if x is not None and y is not None:
            raise ValueError("Only univariate distributions are supported: pass either x or y.")
        frame, labels = long_frame(data, x=x, y=y, hue=hue, dropna=("x", "y"))
    role = "x" if "x" in frame.columns else "y"
    values = frame[role].astype(float)
    if "hue" in frame.columns:
        levels = categorical_order(frame["hue"], hue_order)
        groups = {level: values[frame["hue"] == level].to_numpy() for level in levels}
        groups = {level: group for level, group in groups.items() if len(group)}
    else:
        groups = {None: values.to_numpy()}
    return _Distribution(groups, "v" if role == "x" else "h", labels.get(role), labels.get("hue"), "hue" in frame)


def _colors(dist: _Distribution, palette: ty.Any, color: ty.Any) -> dict[ty.Any, np.ndarray]:
    """Colors per hue level (or the single group)."""
    if dist.has_hue:
        return level_colors(list(dist.groups), palette, color)
    return {None: level_colors([0], palette, color)[0]}


def _label_axes(viewer: ViewerModel, dist: _Distribution, value_label: str) -> None:
    """Name the observation axis after the variable and the other after the statistic."""
    if dist.orient == "v":
        cm.set_axis_labels(viewer, dist.label, value_label)
    else:
        cm.set_axis_labels(viewer, value_label, dist.label)


def kdeplot(
    viewer: ViewerModel,
    data: ty.Any = None,
    *,
    x: ty.Any = None,
    y: ty.Any = None,
    hue: ty.Any = None,
    hue_order: list | None = None,
    palette: ty.Any = None,
    color: ty.Any = None,
    fill: bool = False,
    common_norm: bool = True,
    cumulative: bool = False,
    bw_method: ty.Any = "scott",
    bw_adjust: float = 1.0,
    gridsize: int = 200,
    cut: float = 3,
    clip: tuple[float | None, float | None] | None = None,
    linewidth: float = 2.0,
    alpha: float = 0.25,
    legend: bool = True,
    name: str = "kdeplot",
) -> list[Layer]:
    """Draw univariate kernel density estimates, one curve per hue level.

    Parameters
    ----------
    viewer : ViewerModel
        Viewer to draw on.
    data : DataFrame, dict or array, optional
        Long-form table (with ``x``/``y``/``hue`` naming columns), wide-form table (each column a level) or a
        plain array of observations.
    x, y : str or array-like, optional
        Observations along x (density on y) or along y (density on x).
    hue : str or array-like, optional
        Grouping variable; one curve per level.
    hue_order, palette, color
        Level order and colors, as in seaborn.
    fill : bool
        Fill the area under each curve.
    common_norm : bool
        Scale each curve by its share of observations so all curves integrate to 1 together.
    cumulative : bool
        Draw the cumulative distribution instead of the density.
    bw_method, bw_adjust, gridsize, cut, clip
        KDE parameters, as in seaborn.
    linewidth : float
        Curve width in screen pixels.
    alpha : float
        Opacity of the fill.
    legend : bool
        Show a legend for hue levels.
    name : str
        Prefix for created layer names.

    Returns
    -------
    list of Layer
        Created layers in drawing order.
    """
    dist = _distribution(data, x, y, hue, hue_order)
    colors = _colors(dist, palette, color)
    curves, curve_colors, areas = [], [], []
    for level, values in dist.groups.items():
        support, density = kde(
            values,
            bw_method=bw_method,
            bw_adjust=bw_adjust,
            gridsize=gridsize,
            cut=cut,
            clip=clip,
            cumulative=cumulative,
        )
        if not len(support):
            continue
        if common_norm and dist.has_hue:
            density = density * len(values) / dist.total
        curves.append(np.column_stack((support, density)))
        curve_colors.append(colors[level])
        areas.append(np.column_stack((support, np.zeros_like(density), density)))

    layers: list[Layer | None] = []
    if fill and areas:
        layers.append(
            viewer.add_areas(
                areas,
                orientation="vertical" if dist.orient == "v" else "horizontal",
                fill_color=curve_colors,
                border_width=0,
                opacity=alpha,
                name=f"{name} fill",
            )
        )
    if curves:
        layers.append(
            cm.add_segments(viewer, curves, dist.orient, color=curve_colors, width=linewidth, name=f"{name} curves")
        )
    _label_axes(viewer, dist, "Cumulative" if cumulative else "Density")
    entries = cm.legend_entries(colors, marker="hbar") if dist.has_hue else []
    return cm.finish(viewer, layers, entries, legend)


def _kde_scale(stat: str, n: int, bin_width: float) -> float:
    """Factor converting a probability density to the histogram's ``stat`` units."""
    return {
        "count": n * bin_width,
        "frequency": n,
        "density": 1.0,
        "probability": bin_width,
        "proportion": bin_width,
        "percent": bin_width * 100,
    }[stat]


def histplot(
    viewer: ViewerModel,
    data: ty.Any = None,
    *,
    x: ty.Any = None,
    y: ty.Any = None,
    hue: ty.Any = None,
    hue_order: list | None = None,
    palette: ty.Any = None,
    color: ty.Any = None,
    stat: str = "count",
    bins: ty.Any = "auto",
    binwidth: float | None = None,
    binrange: tuple[float, float] | None = None,
    discrete: bool = False,
    cumulative: bool = False,
    common_bins: bool = True,
    common_norm: bool = True,
    multiple: str = "layer",
    shrink: float = 1.0,
    kde: bool = False,
    kde_kws: dict | None = None,
    alpha: float | None = None,
    linecolor: ty.Any = "transparent",
    linewidth: float = 1.0,
    legend: bool = True,
    name: str = "histplot",
) -> list[Layer]:
    """Draw histograms of univariate observations, optionally split and arranged by hue.

    Parameters
    ----------
    viewer : ViewerModel
        Viewer to draw on.
    data, x, y, hue, hue_order, palette, color
        As in :func:`kdeplot`.
    stat : {"count", "frequency", "density", "probability", "proportion", "percent"}
        Statistic computed in each bin.
    bins, binwidth, binrange, discrete
        Bin definition, as in seaborn.
    cumulative : bool
        Accumulate bin heights.
    common_bins : bool
        Use the same bins for every hue level (required for ``multiple`` other than ``"layer"``).
    common_norm : bool
        Normalize normalized stats over all levels rather than within each level.
    multiple : {"layer", "stack", "dodge", "fill"}
        Arrangement of hue levels.
    shrink : float
        Fraction of the bin width each bar occupies.
    kde : bool
        Overlay a kernel density estimate scaled to the histogram.
    kde_kws : dict, optional
        Extra :func:`kdeplot` parameters for the overlay.
    alpha : float, optional
        Bar opacity (defaults to 0.5 when layered hue levels overlap, otherwise 0.75).
    linecolor, linewidth
        Bar outline style.
    legend : bool
        Show a legend for hue levels.
    name : str
        Prefix for created layer names.

    Returns
    -------
    list of Layer
        Created layers in drawing order.
    """
    if multiple not in {"layer", "stack", "dodge", "fill"}:
        raise ValueError("multiple must be 'layer', 'stack', 'dodge' or 'fill'.")
    dist = _distribution(data, x, y, hue, hue_order)
    colors = _colors(dist, palette, color)
    if multiple != "layer":
        common_bins = True
    shared = histogram_bins(dist.all_values, bins=bins, binwidth=binwidth, binrange=binrange, discrete=discrete)

    heights: dict[ty.Any, tuple[np.ndarray, np.ndarray]] = {}
    for level, values in dist.groups.items():
        edges = (
            shared
            if common_bins
            else histogram_bins(values, bins=bins, binwidth=binwidth, binrange=binrange, discrete=discrete)
        )
        counts = histogram(values, edges, stat=stat, cumulative=cumulative)
        if common_norm and dist.has_hue and stat in _NORMALIZED_STATS:
            counts = counts * len(values) / dist.total
        heights[level] = (edges, counts)

    n_levels = len(heights)
    baseline = np.zeros(len(shared) - 1)
    totals = np.sum([counts for _, counts in heights.values()], axis=0) if multiple == "fill" else None
    layers: list[Layer | None] = []
    for hue_index, (level, (edges, counts)) in enumerate(heights.items()):
        widths = np.diff(edges) * shrink
        centers = edges[:-1] + np.diff(edges) / 2
        base = np.zeros_like(counts)
        if multiple in {"stack", "fill"}:
            if totals is not None:
                counts = np.divide(counts, totals, out=np.zeros_like(counts), where=totals > 0)
            base = baseline.copy()
            baseline = baseline + counts
        elif multiple == "dodge":
            widths = widths / n_levels
            centers = centers - np.diff(edges) * shrink / 2 + widths * (hue_index + 0.5)
        opacity = alpha if alpha is not None else (0.5 if multiple == "layer" and n_levels > 1 else 0.75)
        layers.append(
            viewer.add_bar(
                np.column_stack((centers, base + counts, base, widths)),
                orientation=cm.bar_orientation(dist.orient),
                fill_color=colors[level],
                border_color=linecolor,
                border_width=linewidth,
                opacity=opacity,
                name=name if level is None else f"{name} [{level}]",
            )
        )

    if kde:
        kws = dict(kde_kws or {})
        curves, curve_colors = [], []
        for level, values in dist.groups.items():
            support, density = _kde_for(values, **kws)
            if not len(support):
                continue
            edges = heights[level][0]
            scale = _kde_scale(stat, len(values), float(np.mean(np.diff(edges))))
            if common_norm and dist.has_hue and stat in _NORMALIZED_STATS:
                scale *= len(values) / dist.total
            curves.append(np.column_stack((support, density * scale)))
            curve_colors.append(colors[level])
        if curves:
            layers.append(cm.add_segments(viewer, curves, dist.orient, color=curve_colors, width=2, name=f"{name} kde"))

    _label_axes(viewer, dist, stat.capitalize())
    entries = cm.legend_entries(colors) if dist.has_hue else []
    return cm.finish(viewer, layers, entries, legend)


def _kde_for(values: np.ndarray, **kws: ty.Any) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate a KDE using only the keyword arguments ``kde`` understands."""
    allowed = {"bw_method", "bw_adjust", "gridsize", "cut", "clip", "cumulative"}
    return kde(values, **{key: value for key, value in kws.items() if key in allowed})


def distplot(
    viewer: ViewerModel,
    a: ty.Any = None,
    *,
    data: ty.Any = None,
    x: ty.Any = None,
    y: ty.Any = None,
    hue: ty.Any = None,
    hue_order: list | None = None,
    palette: ty.Any = None,
    color: ty.Any = None,
    bins: ty.Any = "auto",
    hist: bool = True,
    kde: bool = True,
    rug: bool = False,
    rug_height: float = 0.025,
    hist_kws: dict | None = None,
    kde_kws: dict | None = None,
    legend: bool = True,
    name: str = "distplot",
) -> list[Layer]:
    """Draw a density-normalized histogram with a KDE curve and optional rug (seaborn's classic ``distplot``).

    Parameters
    ----------
    viewer : ViewerModel
        Viewer to draw on.
    a : array-like, optional
        Observations (shortcut for ``data`` when no ``x``/``y`` is given).
    data, x, y, hue, hue_order, palette, color
        As in :func:`kdeplot`.
    bins : str, int or array
        Histogram bins.
    hist, kde, rug : bool
        Which components to draw.
    rug_height : float
        Rug tick length as a fraction of the highest density.
    hist_kws, kde_kws : dict, optional
        Extra :func:`histplot` / :func:`kdeplot` parameters.
    legend : bool
        Show a legend for hue levels.
    name : str
        Prefix for created layer names.

    Returns
    -------
    list of Layer
        Created layers in drawing order.
    """
    source = a if a is not None else data
    common = {"x": x, "y": y, "hue": hue, "hue_order": hue_order, "palette": palette, "color": color}
    layers: list[Layer] = []
    if hist:
        hist_options = {"stat": "density", "bins": bins, "legend": legend, "name": f"{name} hist", **(hist_kws or {})}
        layers += histplot(viewer, source, **common, **hist_options)
    if kde:
        kde_options = {"legend": legend and not hist, "name": f"{name} kde", **(kde_kws or {})}
        layers += kdeplot(viewer, source, **common, **kde_options)
    if rug:
        dist = _distribution(source, x, y, hue, hue_order)
        colors = _colors(dist, palette, color)
        peak = max((np.max(_kde_for(values)[1], initial=0) for values in dist.groups.values()), default=1.0) or 1.0
        length = rug_height * peak
        ticks, tick_colors = [], []
        for level, values in dist.groups.items():
            ticks += [((value, 0.0), (value, -length)) for value in values]
            tick_colors += [colors[level]] * len(values)
        layer = cm.add_segments(viewer, ticks, dist.orient, color=tick_colors, width=1, name=f"{name} rug")
        if layer is not None:
            layers.append(layer)
        cm.fit_view(viewer)
    return layers
