"""Categorical statistical plots: box, boxen, violin, bar, strip and swarm."""

from __future__ import annotations

import typing as ty
from uuid import uuid4

import numpy as np

from napari_plot.stats import _common as cm
from napari_plot.stats._data import CategoricalData, normalize_categorical
from napari_plot.stats._estimators import aggregate, beeswarm, box_stats, kde, letter_values, strip_jitter
from napari_plot.stats._palette import categorical_color_fn, desaturate, level_colors, to_rgba

if ty.TYPE_CHECKING:
    from napari.layers import Layer

    from napari_plot.components.viewer_model import ViewerModel

ColorFn = ty.Callable[[int, ty.Any], np.ndarray]


def _prepare(
    viewer: ViewerModel,
    data: ty.Any,
    x: ty.Any,
    y: ty.Any,
    hue: ty.Any,
    order: list | None,
    hue_order: list | None,
    orient: str | None,
    palette: ty.Any,
    color: ty.Any,
    saturation: float = 1.0,
) -> tuple[CategoricalData, ColorFn, list[dict]]:
    """Normalize data, label the categorical axis and resolve colors and hue legend entries."""
    cat = normalize_categorical(data, x=x, y=y, hue=hue, order=order, hue_order=hue_order, orient=orient)
    cm.apply_categorical_axis(viewer, cat)
    color_fn = categorical_color_fn(cat, palette, color)
    colors = level_colors(cat.hue_levels, palette, color) if cat.hue_levels else {}
    if saturation != 1:
        base_fn = color_fn

        def color_fn(index: int, level: ty.Any) -> np.ndarray:
            return desaturate(base_fn(index, level), saturation)

        colors = {level: desaturate(rgba, saturation) for level, rgba in colors.items()}
    return cat, color_fn, cm.legend_entries(colors)


def _group_info(cat: CategoricalData, index: int, level: ty.Any, values: np.ndarray) -> dict[str, ty.Any]:
    """Describe one plotted group; stored in ``layer.metadata["groups"]`` so hover/click can identify it."""
    q1, median, q3 = np.percentile(values, [25, 50, 75]) if len(values) else (np.nan, np.nan, np.nan)
    return {
        "category": cat.labels[index],
        "hue": level,
        "n": len(values),
        "median": float(median),
        "q1": float(q1),
        "q3": float(q3),
    }


def _with_groups(layer: Layer | None, groups: list[dict[str, ty.Any]]) -> Layer | None:
    """Attach per-element group descriptions to a layer (indexed like the bars/areas it draws)."""
    if layer is not None:
        layer.metadata["groups"] = groups
    return layer


def _layer_name(name: str, level: ty.Any, role: str) -> str:
    """Return ``"name role"`` or ``"name [level] role"`` for hue-split layers."""
    return f"{name} {role}" if level is None else f"{name} [{level}] {role}"


def boxplot(
    viewer: ViewerModel,
    data: ty.Any = None,
    *,
    x: ty.Any = None,
    y: ty.Any = None,
    hue: ty.Any = None,
    order: list | None = None,
    hue_order: list | None = None,
    orient: str | None = None,
    palette: ty.Any = None,
    color: ty.Any = None,
    width: float = 0.8,
    dodge: bool = True,
    saturation: float = 1.0,
    whis: float | tuple[float, float] = 1.5,
    linecolor: ty.Any = "lightgray",
    linewidth: float = 1.5,
    showfliers: bool = True,
    fliersize: float = 5,
    legend: bool = True,
    name: str = "boxplot",
) -> list[Layer]:
    """Draw box-and-whisker plots of values grouped by category (and hue).

    Parameters
    ----------
    viewer : ViewerModel
        Viewer to draw on.
    data : DataFrame, dict, array or sequence of arrays, optional
        Long-form table (with ``x``/``y``/``hue`` naming columns) or wide-form data whose columns become
        categories.
    x, y, hue : str or array-like, optional
        Column names or vectors. The non-numeric of ``x``/``y`` is the categorical axis.
    order, hue_order : list, optional
        Order of category and hue levels.
    orient : {"v", "h"}, optional
        Orientation; inferred from the data types when omitted.
    palette : str, list or dict, optional
        seaborn palette for hue levels (or categories when no hue is given).
    color : color, optional
        Single color for all boxes when no palette/hue is used.
    width : float
        Width of each category slot in data units.
    dodge : bool
        Place hue levels side by side instead of on top of each other.
    saturation : float
        Fraction of the original color saturation to keep (seaborn uses 0.75 by default).
    whis : float or (float, float)
        Whisker reach as a multiple of the IQR, or percentile bounds.
    linecolor, linewidth : color, float
        Style of whiskers, caps and medians (width in screen pixels).
    showfliers : bool
        Whether to draw outliers.
    fliersize : float
        Outlier marker size in screen pixels.
    legend : bool
        Show a legend for hue levels.
    name : str
        Prefix for created layer names.

    Returns
    -------
    list of Layer
        Created layers in drawing order.
    """
    cat, color_fn, entries = _prepare(viewer, data, x, y, hue, order, hue_order, orient, palette, color, saturation)
    line_rgba = to_rgba(linecolor)
    layers: list[Layer | None] = []
    for level, cells, element in cm.iter_cells(cat, width, dodge):
        if not cells:
            continue
        boxes, segments, fliers, fill, groups = [], [], [], [], []
        for index, position, values in cells:
            stats = box_stats(values, whis)
            half = element / 2
            boxes.append((position, stats["q3"], stats["q1"], element))
            fill.append(color_fn(index, level))
            groups.append(_group_info(cat, index, level, values))
            segments += [
                ((position, stats["q1"]), (position, stats["whislo"])),
                ((position, stats["q3"]), (position, stats["whishi"])),
                ((position - half / 2, stats["whislo"]), (position + half / 2, stats["whislo"])),
                ((position - half / 2, stats["whishi"]), (position + half / 2, stats["whishi"])),
                ((position - half, stats["med"]), (position + half, stats["med"])),
            ]
            fliers += [(position, value) for value in stats["fliers"]]
        layers.append(
            _with_groups(
                viewer.add_bar(
                    np.asarray(boxes),
                    orientation=cm.bar_orientation(cat.orient),
                    fill_color=fill,
                    border_color=line_rgba,
                    border_width=linewidth,
                    name=_layer_name(name, level, "boxes"),
                ),
                groups,
            )
        )
        layers.append(
            cm.add_segments(
                viewer, segments, cat.orient, color=line_rgba, width=linewidth, name=_layer_name(name, level, "lines")
            )
        )
        if showfliers and fliers:
            position, value = np.asarray(fliers).T
            layers.append(
                cm.add_points(
                    viewer,
                    position,
                    value,
                    cat.orient,
                    face_color="transparent",
                    border_color=line_rgba,
                    size=fliersize,
                    name=_layer_name(name, level, "fliers"),
                )
            )
    return cm.finish(viewer, layers, entries, legend)


def boxenplot(
    viewer: ViewerModel,
    data: ty.Any = None,
    *,
    x: ty.Any = None,
    y: ty.Any = None,
    hue: ty.Any = None,
    order: list | None = None,
    hue_order: list | None = None,
    orient: str | None = None,
    palette: ty.Any = None,
    color: ty.Any = None,
    width: float = 0.8,
    dodge: bool = True,
    saturation: float = 1.0,
    k_depth: str | int = "tukey",
    width_method: str = "exponential",
    outlier_prop: float = 0.007,
    trust_alpha: float = 0.05,
    linecolor: ty.Any = "lightgray",
    linewidth: float = 1.0,
    showfliers: bool = True,
    fliersize: float = 5,
    legend: bool = True,
    name: str = "boxenplot",
) -> list[Layer]:
    """Draw letter-value (boxen) plots: nested boxes for successively finer quantiles.

    Parameters are as for :func:`boxplot`, plus ``k_depth`` (``"tukey"``, ``"proportion"``, ``"trustworthy"``,
    ``"full"`` or an int), ``width_method`` (``"exponential"``, ``"linear"`` or ``"area"``), ``outlier_prop`` and
    ``trust_alpha`` which follow seaborn's ``boxenplot``.

    Returns
    -------
    list of Layer
        Created layers in drawing order.
    """
    from napari_plot.stats._seaborn import light_palette

    cat, color_fn, entries = _prepare(viewer, data, x, y, hue, order, hue_order, orient, palette, color, saturation)
    line_rgba = to_rgba(linecolor)
    layers: list[Layer | None] = []
    for level, cells, element in cm.iter_cells(cat, width, dodge):
        if not cells:
            continue
        boxes, fill, medians, fliers, groups = [], [], [], [], []
        for index, position, values in cells:
            letters = letter_values(values, k_depth, outlier_prop, trust_alpha)
            info = _group_info(cat, index, level, values)
            levels, edges, k = letters["levels"], letters["values"], letters["k"]
            exponent = (levels - 1 - k).astype(float)
            if width_method == "linear":
                relative = levels + 1.0
            elif width_method == "exponential":
                relative = 2**exponent
            elif width_method == "area":
                tails = levels < (k - 1)
                relative = 2 ** (exponent - tails) / np.maximum(np.diff(edges), np.finfo(float).eps)
            else:
                raise ValueError("width_method must be 'exponential', 'linear' or 'area'.")
            widths = relative / relative.max() * element
            cmap = light_palette(tuple(color_fn(index, level)[:3]), as_cmap=True)
            shades = cmap(2 ** ((exponent + 2) / 3))
            # Draw wide (inner) boxes last so they sit on top of the narrower tails.
            for box in np.argsort(widths, kind="stable"):
                boxes.append((position, edges[box + 1], edges[box], widths[box]))
                fill.append(shades[box])
                groups.append(info)
            half = element / 2
            medians.append(((position - half, letters["median"]), (position + half, letters["median"])))
            fliers += [(position, value) for value in letters["fliers"]]
        layers.append(
            _with_groups(
                viewer.add_bar(
                    np.asarray(boxes),
                    orientation=cm.bar_orientation(cat.orient),
                    fill_color=fill,
                    border_color=line_rgba,
                    border_width=linewidth,
                    name=_layer_name(name, level, "boxes"),
                ),
                groups,
            )
        )
        layers.append(
            cm.add_segments(
                viewer,
                medians,
                cat.orient,
                color=line_rgba,
                width=linewidth * 2,
                name=_layer_name(name, level, "medians"),
            )
        )
        if showfliers and fliers:
            position, value = np.asarray(fliers).T
            layers.append(
                cm.add_points(
                    viewer,
                    position,
                    value,
                    cat.orient,
                    face_color="transparent",
                    border_color=line_rgba,
                    size=fliersize,
                    name=_layer_name(name, level, "fliers"),
                )
            )
    return cm.finish(viewer, layers, entries, legend)


def violinplot(
    viewer: ViewerModel,
    data: ty.Any = None,
    *,
    x: ty.Any = None,
    y: ty.Any = None,
    hue: ty.Any = None,
    order: list | None = None,
    hue_order: list | None = None,
    orient: str | None = None,
    palette: ty.Any = None,
    color: ty.Any = None,
    width: float = 0.8,
    dodge: bool = True,
    saturation: float = 1.0,
    split: bool = False,
    inner: str | None = "box",
    density_norm: str = "area",
    common_norm: bool = False,
    bw_method: ty.Any = "scott",
    bw_adjust: float = 1.0,
    cut: float = 2,
    gridsize: int = 100,
    linecolor: ty.Any = "lightgray",
    linewidth: float = 1.0,
    legend: bool = True,
    name: str = "violinplot",
    group: str | None = None,
) -> list[Layer]:
    """Draw violin plots: mirrored kernel density estimates of values per category (and hue).

    Parameters are as for :func:`boxplot`, plus:

    split : bool
        With exactly two hue levels, draw one half-violin per level instead of dodging.
    inner : {"box", "quart", "stick", "point", None}
        Representation of the observations inside each violin.
    density_norm : {"area", "count", "width"}
        Scale violins to equal area, to their number of observations, or to equal width.
    common_norm : bool
        Normalize the density across all violins rather than within each category.
    group : str, optional
        Shared layer group ID. A fresh ID is generated when omitted or None.
    bw_method, bw_adjust, cut, gridsize
        KDE parameters, as in seaborn.

    Returns
    -------
    list of Layer
        Created layers in drawing order.
    """
    if density_norm not in {"area", "count", "width"}:
        raise ValueError("density_norm must be 'area', 'count' or 'width'.")
    cat, color_fn, entries = _prepare(viewer, data, x, y, hue, order, hue_order, orient, palette, color, saturation)
    split = split and cat.hue_levels is not None and len(cat.hue_levels) == 2
    line_rgba = to_rgba(linecolor)
    metadata = {"napari_plot.group": group if group is not None else str(uuid4())}

    # Estimate all densities first so the normalization can be shared between violins.
    groups = []
    for hue_index, (level, cells, element) in enumerate(cm.iter_cells(cat, width, dodge and not split)):
        for index, position, values in cells:
            support, density = kde(values, bw_method=bw_method, bw_adjust=bw_adjust, cut=cut, gridsize=gridsize)
            if not len(support):  # degenerate group: draw a flat line at its value
                support, density = np.array([values[0], values[0]]), np.array([1.0, 1.0])
            groups.append((hue_index, level, index, position, values, support, density, element))
    if not groups:
        return cm.finish(viewer, [])
    if common_norm:  # weight each density by its share of all observations
        total = sum(len(group[4]) for group in groups)
        groups = [(*group[:6], group[6] * len(group[4]) / total, group[7]) for group in groups]
    peak = 1.0
    if density_norm == "area":
        peak = max(group[6].max() for group in groups)
    elif density_norm == "count":
        peak = max(group[6].max() * len(group[4]) for group in groups)

    areas, fill, area_groups, inner_lines, inner_points = [], [], [], [], []
    for hue_index, level, index, position, values, support, density, element in groups:
        if density_norm == "width":
            scaled = density / density.max()
        elif density_norm == "count":
            scaled = density * len(values) / peak
        else:
            scaled = density / peak
        half = scaled * element / 2
        if split and hue_index == 0:
            lo, hi = position - half, np.full_like(half, position)
        elif split:
            lo, hi = np.full_like(half, position), position + half
        else:
            lo, hi = position - half, position + half
        areas.append(np.column_stack((support, lo, hi)))
        fill.append(color_fn(index, level))
        area_groups.append(_group_info(cat, index, level, values))

        side = -1 if split and hue_index == 0 else 1
        if inner == "box":
            stats = box_stats(values)
            inner_lines.append((((position, stats["whislo"]), (position, stats["whishi"])), 1.0))
            inner_lines.append((((position, stats["q1"]), (position, stats["q3"])), 4.0))
            inner_points.append((position, stats["med"]))
        elif inner in {"quart", "stick"}:
            marks = np.percentile(values, [25, 50, 75]) if inner == "quart" else values
            for value in marks:
                reach = np.interp(value, support, half)
                start = position if split else position - reach
                end = position + side * reach if split else position + reach
                inner_lines.append((((start, value), (end, value)), 1.0))
        elif inner == "point":
            inner_points += [(position, value) for value in values]
        elif inner is not None:
            raise ValueError("inner must be 'box', 'quart', 'stick', 'point' or None.")

    layers: list[Layer | None] = [
        _with_groups(
            viewer.add_areas(
                areas,
                orientation=cm.areas_orientation(cat.orient),
                fill_color=fill,
                border_color=line_rgba,
                border_width=linewidth,
                name=f"{name} bodies",
                metadata=metadata,
            ),
            area_groups,
        )
    ]
    for line_width in sorted({scale for _, scale in inner_lines}):
        segments = [segment for segment, scale in inner_lines if scale == line_width]
        layers.append(
            cm.add_segments(
                viewer,
                segments,
                cat.orient,
                color=line_rgba,
                width=line_width * linewidth,
                name=f"{name} inner",
                metadata=metadata,
            )
        )
    if inner_points:
        position, value = np.asarray(inner_points).T
        layers.append(
            cm.add_points(
                viewer,
                position,
                value,
                cat.orient,
                face_color="white" if inner == "box" else line_rgba,
                size=5 if inner == "box" else 3,
                name=f"{name} inner points",
                metadata=metadata,
            )
        )
    return cm.finish(viewer, layers, entries, legend)


def barplot(
    viewer: ViewerModel,
    data: ty.Any = None,
    *,
    x: ty.Any = None,
    y: ty.Any = None,
    hue: ty.Any = None,
    order: list | None = None,
    hue_order: list | None = None,
    orient: str | None = None,
    palette: ty.Any = None,
    color: ty.Any = None,
    estimator: ty.Any = "mean",
    errorbar: ty.Any = ("ci", 95),
    n_boot: int = 1000,
    seed: ty.Any = None,
    width: float = 0.8,
    dodge: bool = True,
    err_color: ty.Any = "lightgray",
    err_width: float = 1.5,
    capsize: float = 0.0,
    linecolor: ty.Any = "transparent",
    linewidth: float = 1.0,
    legend: bool = True,
    name: str = "barplot",
) -> list[Layer]:
    """Draw (grouped) bars of a point estimate per category with error bars.

    Parameters are as for :func:`boxplot`, plus:

    estimator : str or callable
        Statistic per group (``"mean"``, ``"median"``, ``np.sum``, ...).
    errorbar : str, (str, float), callable or None
        ``"ci"``, ``"pi"``, ``"se"``, ``"sd"`` with optional level, as in seaborn. None hides error bars.
    n_boot, seed
        Bootstrap settings for ``"ci"``.
    err_color, err_width : color, float
        Error bar style (width in screen pixels).
    capsize : float
        Error bar cap length in screen pixels.

    Returns
    -------
    list of Layer
        Created layers in drawing order.
    """
    cat, color_fn, entries = _prepare(viewer, data, x, y, hue, order, hue_order, orient, palette, color)
    layers: list[Layer | None] = []
    errors = []
    for level, cells, element in cm.iter_cells(cat, width, dodge):
        if not cells:
            continue
        bars, fill, groups = [], [], []
        for index, position, values in cells:
            estimate, low, high = aggregate(values, estimator, errorbar, n_boot, seed)
            bars.append((position, estimate))
            fill.append(color_fn(index, level))
            groups.append(_group_info(cat, index, level, values))
            if np.isfinite(low) and np.isfinite(high):
                errors.append((position, estimate, estimate - low, high - estimate))
        layers.append(
            _with_groups(
                viewer.add_bar(
                    np.asarray(bars),
                    orientation=cm.bar_orientation(cat.orient),
                    width=element,
                    fill_color=fill,
                    border_color=linecolor,
                    border_width=linewidth,
                    name=_layer_name(name, level, "bars"),
                ),
                groups,
            )
        )
    if errors:
        position, estimate, minus, plus = np.asarray(errors).T
        nan = np.full_like(position, np.nan)
        x, y = cm.to_xy(position, estimate, cat.orient)
        offsets = (nan, nan, minus, plus) if cat.orient == "v" else (minus, plus, nan, nan)
        layers.append(
            viewer.add_error_bar(
                np.column_stack((x, y, *offsets)),
                color=err_color,
                width=err_width,
                cap_size=capsize,
                name=f"{name} errors",
            )
        )
    return cm.finish(viewer, layers, entries, legend)


def _scatter_categorical(
    viewer: ViewerModel,
    cat: CategoricalData,
    color_fn: ColorFn,
    entries: list[dict],
    offsets_fn: ty.Callable[[int, ty.Any, float, np.ndarray, float], np.ndarray],
    *,
    width: float,
    dodge: bool,
    size: float,
    linecolor: ty.Any,
    linewidth: float,
    legend: bool,
    name: str,
) -> list[Layer]:
    """Shared body of strip and swarm plots: one Scatter layer per hue level.

    Each layer has ``category`` and ``hue`` features naming the group of every point, for hover/click lookups.
    """
    layers: list[Layer | None] = []
    for level, cells, element in cm.iter_cells(cat, width, dodge):
        if not cells:
            continue
        positions, values, colors, categories = [], [], [], []
        for index, position, group in cells:
            positions.append(offsets_fn(index, level, position, group, element))
            values.append(group)
            colors.append(np.broadcast_to(color_fn(index, level), (len(group), 4)))
            categories += [cat.labels[index]] * len(group)
        layers.append(
            cm.add_points(
                viewer,
                np.concatenate(positions),
                np.concatenate(values),
                cat.orient,
                face_color=np.concatenate(colors),
                border_color=linecolor,
                border_width=linewidth,
                border_width_is_relative=False,
                size=size,
                features={"category": categories, "hue": [level] * len(categories)},
                name=name if level is None else f"{name} [{level}]",
            )
        )
    return cm.finish(viewer, layers, entries, legend)


def stripplot(
    viewer: ViewerModel,
    data: ty.Any = None,
    *,
    x: ty.Any = None,
    y: ty.Any = None,
    hue: ty.Any = None,
    order: list | None = None,
    hue_order: list | None = None,
    orient: str | None = None,
    palette: ty.Any = None,
    color: ty.Any = None,
    jitter: float | bool = True,
    dodge: bool = False,
    width: float = 0.8,
    size: float = 6,
    linecolor: ty.Any = "transparent",
    linewidth: float = 0.0,
    seed: ty.Any = None,
    legend: bool = True,
    name: str = "stripplot",
) -> list[Layer]:
    """Draw every observation as a point, jittered along the categorical axis.

    Parameters are as for :func:`boxplot`, plus ``jitter`` (True for the default amount, or the half-width of the
    jitter in data units), ``size`` (marker size in screen pixels), ``linewidth`` (marker border width in screen
    pixels) and ``seed`` for reproducible jitter.

    Returns
    -------
    list of Layer
        Created layers in drawing order.
    """
    cat, color_fn, entries = _prepare(viewer, data, x, y, hue, order, hue_order, orient, palette, color)
    rng = np.random.default_rng(seed)

    def offsets(_index: int, _level: ty.Any, position: float, group: np.ndarray, element: float) -> np.ndarray:
        half_width = 0.2 * element if jitter is True else float(jitter or 0)
        return position + strip_jitter(len(group), half_width, rng)

    return _scatter_categorical(
        viewer,
        cat,
        color_fn,
        entries,
        offsets,
        width=width,
        dodge=dodge,
        size=size,
        linecolor=linecolor,
        linewidth=linewidth,
        legend=legend,
        name=name,
    )


def swarmplot(
    viewer: ViewerModel,
    data: ty.Any = None,
    *,
    x: ty.Any = None,
    y: ty.Any = None,
    hue: ty.Any = None,
    order: list | None = None,
    hue_order: list | None = None,
    orient: str | None = None,
    palette: ty.Any = None,
    color: ty.Any = None,
    dodge: bool = False,
    width: float = 0.8,
    size: float = 6,
    linecolor: ty.Any = "transparent",
    linewidth: float = 0.0,
    warn_thresh: float = 0.05,
    legend: bool = True,
    name: str = "swarmplot",
) -> list[Layer]:
    """Draw a beeswarm, spreading points along the categorical axis to avoid overlap.

    Point positions are computed for the canvas size at call time; zooming changes the apparent spacing.
    With ``dodge=False``, hue levels share a swarm in each category. ``warn_thresh`` sets the fraction of
    points that can reach the gutters before seaborn warns. Set it to 1 to suppress crowding warnings.
    Other parameters are shared with :func:`stripplot`.

    Returns
    -------
    list of Layer
        Created layers in drawing order.
    """
    cat, color_fn, entries = _prepare(viewer, data, x, y, hue, order, hue_order, orient, palette, color)
    values = cat.all_values
    height_px, width_px = (max(float(v), 1.0) for v in viewer._canvas_size)
    value_px, category_px = (height_px, width_px) if cat.orient == "v" else (width_px, height_px)
    value_span = max(float(np.ptp(values)) * 1.1, 1e-12) if len(values) else 1.0
    value_scale = value_px / value_span
    category_scale = category_px / max(len(cat.categories), 1)

    def layout(position: float, group: np.ndarray, element: float) -> np.ndarray:
        return beeswarm(
            group,
            position,
            (size + linewidth) / 2,
            value_scale,
            category_scale,
            width=element,
            warn_thresh=warn_thresh,
        )

    shared: dict[int, dict[ty.Any, np.ndarray]] = {}
    if cat.hue_levels and len(cat.hue_levels) > 1 and not dodge:
        for index, category in enumerate(cat.categories):
            groups = [cat.values(category, level) for level in cat.hue_levels]
            positions = layout(index, np.concatenate(groups), width)
            splits = np.cumsum([len(group) for group in groups[:-1]])
            shared[index] = dict(zip(cat.hue_levels, np.split(positions, splits), strict=True))

    def offsets(index: int, level: ty.Any, position: float, group: np.ndarray, element: float) -> np.ndarray:
        return shared[index][level] if index in shared else layout(position, group, element)

    return _scatter_categorical(
        viewer,
        cat,
        color_fn,
        entries,
        offsets,
        width=width,
        dodge=dodge,
        size=size,
        linecolor=linecolor,
        linewidth=linewidth,
        legend=legend,
        name=name,
    )
