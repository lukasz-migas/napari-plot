"""Relational plots: scatterplot and lineplot with hue/size/style semantics, plus ``relplot``."""

from __future__ import annotations

import typing as ty

import numpy as np
import pandas as pd

from napari_plot.stats import _common as cm
from napari_plot.stats._data import long_frame
from napari_plot.stats._estimators import aggregate
from napari_plot.stats._palette import level_colors, to_rgba

if ty.TYPE_CHECKING:
    from napari.layers import Layer

    from napari_plot.components.viewer_model import ViewerModel

DEFAULT_MARKERS = ("disc", "x", "square", "triangle_up", "diamond", "cross", "star", "triangle_down", "ring", "clobber")


def _is_numeric(series: pd.Series) -> bool:
    """Whether a semantic variable should be mapped continuously."""
    return pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)


def _map_hue(
    series: pd.Series, order: list | None, palette: ty.Any, color: ty.Any, norm: tuple[float, float] | None
) -> tuple[np.ndarray, list[dict]]:
    """Return per-row colors and legend entries for a hue variable."""
    from napari_plot.stats._seaborn import categorical_order, color_palette

    if _is_numeric(series) and order is None and not isinstance(palette, (dict, list)):
        cmap = color_palette(palette or "viridis", as_cmap=True)
        vmin, vmax = norm if norm is not None else (float(series.min()), float(series.max()))
        scaled = (series.to_numpy(dtype=float) - vmin) / ((vmax - vmin) or 1.0)
        colors = cmap(np.clip(scaled, 0, 1))
        ticks = np.linspace(vmin, vmax, 5)
        entries = [
            {"label": f"{tick:.3g}", "marker": "disc", "color": cmap((tick - vmin) / ((vmax - vmin) or 1.0))}
            for tick in ticks
        ]
        return np.asarray(colors), entries
    levels = categorical_order(series, order)
    mapping = level_colors(levels, palette, color)
    colors = np.stack([mapping[value] for value in series])
    return colors, cm.legend_entries(mapping, marker="disc")


def _map_size(series: pd.Series, order: list | None, sizes: tuple[float, float]) -> np.ndarray:
    """Return per-row marker sizes (screen pixels) for a size variable."""
    from napari_plot.stats._seaborn import categorical_order

    low, high = sizes
    if _is_numeric(series) and order is None:
        values = series.to_numpy(dtype=float)
        span = np.ptp(values) or 1.0
        return low + (values - values.min()) / span * (high - low)
    levels = categorical_order(series, order)
    mapping = dict(zip(levels, np.linspace(high, low, len(levels)), strict=True))
    return np.asarray([mapping[value] for value in series])


def _map_style(series: pd.Series, order: list | None, markers: ty.Any) -> tuple[np.ndarray, list[dict]]:
    """Return per-row marker symbols and legend entries for a style variable."""
    from napari_plot.stats._seaborn import categorical_order

    levels = categorical_order(series, order)
    if isinstance(markers, dict):
        mapping = {level: markers[level] for level in levels}
    else:
        options = list(markers) if markers not in (None, True) else list(DEFAULT_MARKERS)
        mapping = {level: options[i % len(options)] for i, level in enumerate(levels)}
    symbols = np.asarray([mapping[value] for value in series], dtype=object)
    entries = [{"label": str(level), "marker": symbol, "color": "gray"} for level, symbol in mapping.items()]
    return symbols, entries


def scatterplot(
    viewer: ViewerModel,
    data: ty.Any = None,
    *,
    x: ty.Any = None,
    y: ty.Any = None,
    hue: ty.Any = None,
    size: ty.Any = None,
    style: ty.Any = None,
    hue_order: list | None = None,
    hue_norm: tuple[float, float] | None = None,
    size_order: list | None = None,
    style_order: list | None = None,
    palette: ty.Any = None,
    color: ty.Any = None,
    sizes: tuple[float, float] = (4, 14),
    markers: ty.Any = True,
    marker_size: float = 7,
    linecolor: ty.Any = "transparent",
    opacity: float = 1.0,
    legend: bool = True,
    name: str = "scatterplot",
) -> list[Layer]:
    """Draw a scatter plot whose color, size and marker can encode extra variables.

    Parameters
    ----------
    viewer : ViewerModel
        Viewer to draw on.
    data : DataFrame or dict, optional
        Long-form table whose columns are named by ``x``, ``y``, ``hue``, ``size`` and ``style``.
    x, y : str or array-like
        Coordinates.
    hue : str or array-like, optional
        Color grouping; numeric values map onto a colormap (``palette`` names it), others onto a palette.
    size : str or array-like, optional
        Marker size grouping, mapped into the ``sizes`` range (screen pixels).
    style : str or array-like, optional
        Marker symbol grouping, using ``markers`` (list, dict or True for defaults).
    hue_order, hue_norm, size_order, style_order
        Level orders and the numeric hue range.
    palette, color
        Colors, as in seaborn.
    marker_size : float
        Marker size in screen pixels when ``size`` is not given.
    linecolor : color
        Marker outline color.
    opacity : float
        Layer opacity.
    legend : bool
        Show a legend for hue and style levels.
    name : str
        Layer name.

    Returns
    -------
    list of Layer
        Created layers.
    """
    frame, labels = long_frame(data, x=x, y=y, hue=hue, size=size, style=style, dropna=("x", "y"))
    if "x" not in frame or "y" not in frame:
        raise ValueError("scatterplot needs both x and y.")
    entries: list[dict] = []
    face = np.broadcast_to(to_rgba(color) if color is not None else level_colors([0], palette)[0], (len(frame), 4))
    if "hue" in frame:
        face, hue_entries = _map_hue(frame["hue"], hue_order, palette, color, hue_norm)
        entries += hue_entries
    sizes_px = _map_size(frame["size"], size_order, sizes) if "size" in frame else marker_size
    symbols: ty.Any = "disc"
    if "style" in frame:
        symbols, style_entries = _map_style(frame["style"], style_order, markers)
        entries += style_entries
    layer = cm.add_points(
        viewer,
        frame["x"].to_numpy(dtype=float),
        frame["y"].to_numpy(dtype=float),
        "v",
        face_color=np.asarray(face),
        size=sizes_px,
        symbol=symbols,
        border_color=linecolor,
        opacity=opacity,
        name=name,
    )
    cm.set_axis_labels(viewer, labels.get("x"), labels.get("y"))
    return cm.finish(viewer, [layer], entries, legend)


def lineplot(
    viewer: ViewerModel,
    data: ty.Any = None,
    *,
    x: ty.Any = None,
    y: ty.Any = None,
    hue: ty.Any = None,
    hue_order: list | None = None,
    palette: ty.Any = None,
    color: ty.Any = None,
    estimator: ty.Any = "mean",
    errorbar: ty.Any = ("ci", 95),
    n_boot: int = 1000,
    seed: ty.Any = None,
    sort: bool = True,
    err_style: str = "band",
    linewidth: float = 2.0,
    err_alpha: float = 0.2,
    legend: bool = True,
    name: str = "lineplot",
) -> list[Layer]:
    """Draw lines through ``y`` per ``x``, aggregating repeated ``x`` values with an error band.

    Parameters
    ----------
    viewer : ViewerModel
        Viewer to draw on.
    data, x, y, hue, hue_order, palette, color
        As in :func:`scatterplot`; one line per hue level.
    estimator : str, callable or None
        Aggregate of ``y`` at each ``x``; None draws the raw observations.
    errorbar : str, (str, float), callable or None
        Interval around the estimate (``"ci"``, ``"pi"``, ``"se"``, ``"sd"``), as in seaborn.
    n_boot, seed
        Bootstrap settings for ``"ci"``.
    sort : bool
        Sort observations by ``x`` before drawing.
    err_style : {"band", "bars"}
        Draw the interval as a filled band or as error bars.
    linewidth : float
        Line width in screen pixels.
    err_alpha : float
        Opacity of the error band.
    legend : bool
        Show a legend for hue levels.
    name : str
        Prefix for created layer names.

    Returns
    -------
    list of Layer
        Created layers in drawing order.
    """
    from napari_plot.stats._seaborn import categorical_order

    if err_style not in {"band", "bars"}:
        raise ValueError("err_style must be 'band' or 'bars'.")
    frame, labels = long_frame(data, x=x, y=y, hue=hue, dropna=("x", "y"))
    if "x" not in frame or "y" not in frame:
        raise ValueError("lineplot needs both x and y.")
    has_hue = "hue" in frame
    levels = list(categorical_order(frame["hue"], hue_order)) if has_hue else [None]
    colors = level_colors(levels, palette, color) if has_hue else {None: level_colors([0], palette, color)[0]}

    lines, line_colors, bands, band_colors = [], [], [], []
    error_layers: list[Layer | None] = []
    for level in levels:
        group = frame if level is None else frame[frame["hue"] == level]
        if sort:
            group = group.sort_values("x", kind="stable")
        if estimator is None:
            xs, est = group["x"].to_numpy(dtype=float), group["y"].to_numpy(dtype=float)
            low = high = np.full_like(est, np.nan)
        else:
            rows = [
                (value, *aggregate(sub["y"].to_numpy(), estimator, errorbar, n_boot, seed))
                for value, sub in group.groupby("x", sort=sort)
            ]
            xs, est, low, high = (np.asarray(column, dtype=float) for column in zip(*rows, strict=True))
        if not len(xs):
            continue
        lines.append(np.column_stack((xs, est)))
        line_colors.append(colors[level])
        valid = np.isfinite(low) & np.isfinite(high)
        if err_style == "band" and valid.sum() >= 2:
            bands.append(np.column_stack((xs[valid], low[valid], high[valid])))
            band_colors.append(colors[level])
        elif err_style == "bars" and valid.any():
            nan = np.full(valid.sum(), np.nan)
            error_layers.append(
                viewer.add_error_bar(
                    np.column_stack((xs[valid], est[valid], nan, nan, (est - low)[valid], (high - est)[valid])),
                    color=colors[level],
                    width=1.5,
                    name=name if level is None else f"{name} [{level}] errors",
                )
            )

    layers: list[Layer | None] = []
    if bands:
        layers.append(
            viewer.add_areas(bands, fill_color=band_colors, border_width=0, opacity=err_alpha, name=f"{name} errors")
        )
    layers += error_layers
    layers.append(cm.add_segments(viewer, lines, "v", color=line_colors, width=linewidth, name=f"{name} lines"))
    cm.set_axis_labels(viewer, labels.get("x"), labels.get("y"))
    entries = cm.legend_entries(colors, marker="hbar") if has_hue else []
    return cm.finish(viewer, layers, entries, legend)


def relplot(
    viewer: ViewerModel,
    data: ty.Any = None,
    *,
    x: ty.Any = None,
    y: ty.Any = None,
    hue: ty.Any = None,
    size: ty.Any = None,
    style: ty.Any = None,
    kind: str = "scatter",
    **kwargs: ty.Any,
) -> list[Layer]:
    """Draw a relational plot on one canvas: ``kind="scatter"`` (:func:`scatterplot`) or ``"line"`` (:func:`lineplot`).

    Row/column faceting is not supported. Extra keyword arguments go to the selected plot function.

    Returns
    -------
    list of Layer
        Created layers in drawing order.
    """
    if kind == "scatter":
        return scatterplot(viewer, data, x=x, y=y, hue=hue, size=size, style=style, **kwargs)
    if kind == "line":
        if size is not None or style is not None:
            raise ValueError("size and style are only supported for kind='scatter'.")
        return lineplot(viewer, data, x=x, y=y, hue=hue, **kwargs)
    raise ValueError("kind must be 'scatter' or 'line'.")
