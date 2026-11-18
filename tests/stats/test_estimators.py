"""Tests for the shared statistics helpers."""

import numpy as np

from napari_plot.stats._estimators import (
    aggregate,
    beeswarm,
    box_stats,
    histogram,
    histogram_bins,
    kde,
    letter_values,
    strip_jitter,
)


def test_box_stats_match_percentiles() -> None:
    values = np.r_[np.arange(1.0, 21.0), 100.0]
    stats = box_stats(values)
    q1, med, q3 = np.percentile(values, [25, 50, 75])
    assert (stats["q1"], stats["med"], stats["q3"]) == (q1, med, q3)
    assert list(stats["fliers"]) == [100.0]
    assert stats["whishi"] == 20


def test_kde_integrates_to_one_and_handles_degenerate_input() -> None:
    support, density = kde(np.random.default_rng(0).normal(size=500), cut=4)
    assert np.isclose(np.sum(density) * (support[1] - support[0]), 1, atol=0.01)
    assert kde(np.ones(10))[0].size == 0
    assert kde(np.array([1.0]))[0].size == 0


def test_letter_values_are_nested() -> None:
    letters = letter_values(np.random.default_rng(1).normal(size=2000))
    assert letters["k"] > 3
    assert np.all(np.diff(letters["values"]) > 0)


def test_aggregate_interval_contains_estimate() -> None:
    estimate, low, high = aggregate(np.arange(20.0), seed=0, n_boot=200)
    assert low < estimate < high
    estimate, low, high = aggregate(np.arange(20.0), "median", "sd")
    assert estimate == 9.5
    assert np.isclose(high - estimate, np.arange(20.0).std(ddof=1))
    assert np.isnan(aggregate(np.array([1.0]))[1])


def test_histogram_with_shared_edges() -> None:
    values = np.random.default_rng(2).normal(size=300)
    edges = histogram_bins(values, bins=10)
    assert len(edges) == 11
    assert histogram(values, edges).sum() == 300
    assert np.isclose(histogram(values, edges, stat="probability").sum(), 1)


def test_beeswarm_points_do_not_overlap() -> None:
    values = np.random.default_rng(3).normal(size=60)
    offsets = beeswarm(values, center=1, radius=3, value_scale=100, category_scale=200)
    pixels = np.column_stack((offsets * 200, values * 100))
    distances = np.linalg.norm(pixels[:, None] - pixels[None], axis=-1)
    np.fill_diagonal(distances, np.inf)
    assert distances.min() >= 6 - 1e-6
    assert abs(np.median(offsets) - 1) < 0.1
    assert beeswarm(np.empty(0), 0, 1, 1, 1).size == 0


def test_strip_jitter_bounds() -> None:
    jitter = strip_jitter(100, 0.2, seed=0)
    assert np.all(np.abs(jitter) <= 0.2)
    assert np.all(strip_jitter(5, 0) == 0)
