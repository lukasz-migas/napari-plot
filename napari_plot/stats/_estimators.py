"""Statistics shared by the plots, thin wrappers over seaborn / matplotlib estimators."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def box_stats(values: np.ndarray, whis: float | tuple[float, float] = 1.5) -> dict[str, Any]:
    """Return ``med``, ``q1``, ``q3``, ``whislo``, ``whishi`` and ``fliers`` (matplotlib's boxplot_stats)."""
    from matplotlib.cbook import boxplot_stats

    return boxplot_stats(np.asarray(values, dtype=float), whis=whis)[0]


def letter_values(
    values: np.ndarray, k_depth: str | int = "tukey", outlier_prop: float = 0.007, trust_alpha: float = 0.05
) -> dict[str, Any]:
    """Return letter-value boxes (seaborn ``LetterValues``): ``k``, ``levels``, ``values``, ``fliers``, ``median``."""
    from napari_plot.stats._seaborn import LetterValues

    return LetterValues(k_depth, outlier_prop, trust_alpha)(np.asarray(values, dtype=float))


def kde(
    values: np.ndarray,
    *,
    bw_method: Any = "scott",
    bw_adjust: float = 1.0,
    gridsize: int = 200,
    cut: float = 3,
    clip: tuple[float | None, float | None] | None = None,
    cumulative: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(support, density)`` of a Gaussian KDE (seaborn ``KDE``); empty for degenerate input."""
    from napari_plot.stats._seaborn import KDE

    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 2 or np.ptp(values) == 0:
        return np.empty(0), np.empty(0)
    estimator = KDE(
        bw_method=bw_method, bw_adjust=bw_adjust, gridsize=gridsize, cut=cut, clip=clip, cumulative=cumulative
    )
    density, support = estimator(values)
    return support, density


def aggregate(
    values: np.ndarray,
    estimator: Any = "mean",
    errorbar: Any = ("ci", 95),
    n_boot: int = 1000,
    seed: Any = None,
) -> tuple[float, float, float]:
    """Return ``(estimate, low, high)`` using seaborn's ``EstimateAggregator`` (NaN bounds when undefined)."""
    from napari_plot.stats._seaborn import EstimateAggregator

    frame = pd.DataFrame({"v": np.asarray(values, dtype=float)})
    result = EstimateAggregator(estimator, errorbar, n_boot=n_boot, seed=seed)(frame, "v")
    return float(result["v"]), float(result["vmin"]), float(result["vmax"])


def histogram_bins(
    values: np.ndarray,
    *,
    bins: Any = "auto",
    binwidth: float | None = None,
    binrange: tuple[float, float] | None = None,
    discrete: bool = False,
) -> np.ndarray:
    """Return shared bin edges for all groups (seaborn ``Histogram`` bin rules)."""
    from napari_plot.stats._seaborn import Histogram

    estimator = Histogram(bins=bins, binwidth=binwidth, binrange=binrange, discrete=discrete)
    bin_kws = estimator.define_bin_params(np.asarray(values, dtype=float))
    return np.histogram_bin_edges(values, **bin_kws)


def histogram(values: np.ndarray, edges: np.ndarray, *, stat: str = "count", cumulative: bool = False) -> np.ndarray:
    """Return bin heights for the given ``edges`` and seaborn ``stat``."""
    from napari_plot.stats._seaborn import Histogram

    estimator = Histogram(stat=stat, bins=edges, cumulative=cumulative)
    heights, _ = estimator(np.asarray(values, dtype=float))
    return np.asarray(heights, dtype=float)


def beeswarm(
    values: np.ndarray,
    center: float,
    radius: float,
    value_scale: float,
    category_scale: float,
    *,
    width: float | None = None,
    warn_thresh: float = 0.05,
) -> np.ndarray:
    """Return categorical-axis positions that place points without overlap (seaborn ``Beeswarm``).

    The swarm is computed in screen pixels, so the result only stays overlap-free at the zoom level implied by
    the two scales.

    Parameters
    ----------
    values : array
        Point positions along the value axis, in data units.
    center : float
        Category position in data units.
    radius : float
        Point radius in screen pixels.
    value_scale : float
        Screen pixels per value-axis data unit.
    category_scale : float
        Screen pixels per categorical-axis data unit.
    width : float, optional
        Width available to the swarm in categorical-axis data units.
    warn_thresh : float
        Warn when more than this fraction of points land outside the available width.
    """
    from napari_plot.stats._seaborn import Beeswarm

    values = np.asarray(values, dtype=float)
    if len(values) <= 1:
        return np.full(len(values), center, dtype=float)
    xyr = np.column_stack(
        (np.full(len(values), center * category_scale), values * value_scale, np.full(len(values), radius))
    )
    sorter = np.argsort(xyr[:, 1])
    swarm = np.empty_like(xyr)
    layout = Beeswarm(width=0.8 if width is None else width, warn_thresh=warn_thresh)
    swarm[sorter] = layout.beeswarm(xyr[sorter])
    positions = swarm[:, 0] / category_scale
    if width is not None:
        layout.add_gutters(positions, center, float, float)
    return positions


def strip_jitter(n: int, half_width: float, seed: Any = None) -> np.ndarray:
    """Return uniform categorical-axis offsets in ``[-half_width, half_width]``."""
    rng = np.random.default_rng(seed)
    return rng.uniform(-half_width, half_width, n) if half_width > 0 else np.zeros(n)
