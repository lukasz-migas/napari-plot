"""Tests for Vispy axis tick formatting."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

import napari_plot._vispy.components.axis as axis_module
from napari_plot._vispy.components.axis import (
    Ticker,
    _format_ticks,
    _get_major_ticks,
    _tick_label_extents,
    _tick_labels_overlap,
)


def _make_axis(
    *,
    domain: tuple[float, float] = (0.0, 16000.0),
    length: float = 1275.0,
    tick_font_size: float = 24.0,
    vertical: bool = False,
) -> SimpleNamespace:
    """Create the minimal axis interface needed by the custom ticker."""
    end = [0.0, length] if vertical else [length, 0.0]
    return SimpleNamespace(
        domain=np.asarray(domain),
        pos=np.asarray([[0.0, 0.0], end]),
        scale_type="linear",
        transforms=SimpleNamespace(dpi=96.0),
        _stop_at_major=(False, False),
        _text=SimpleNamespace(face="Arial", bold=False, italic=False),
        tick_font_size=tick_font_size,
    )


def test_format_ticks_preserves_single_argument_formatters() -> None:
    calls = []

    def formatter(value: float) -> str:
        calls.append(value)
        return f"{value:.1f}"

    labels = _format_ticks(formatter, np.asarray([0.0, 0.5, 1.0]), 0.5)

    assert labels == ["0.0", "0.5", "1.0"]
    assert calls == [0.0, 0.5, 1.0]


def test_format_ticks_passes_spacing_to_opted_in_formatters() -> None:
    calls = []

    def formatter(value: float, *, tick_spacing: float | None = None) -> str:
        calls.append((value, tick_spacing))
        return str(value)

    labels = _format_ticks(formatter, np.asarray([0.17, 0.171]), 0.001)

    assert labels == ["0.17", "0.171"]
    assert calls == [(0.17, 0.001), (0.171, 0.001)]


def test_format_ticks_supports_kwargs_formatters() -> None:
    calls = []

    def formatter(value: float, **kwargs: float) -> str:
        calls.append((value, kwargs))
        return str(value)

    _format_ticks(formatter, np.asarray([1.0]), 0.25)

    assert calls == [(1.0, {"tick_spacing": 0.25})]


def test_ticker_passes_computed_major_tick_spacing(monkeypatch) -> None:
    major_ticks = np.asarray([0.1675, 0.16875, 0.17, 0.17125])
    monkeypatch.setattr(axis_module, "_get_ticks_talbot", lambda *_args: major_ticks)
    monkeypatch.setattr(axis_module, "_tick_label_extents", lambda _axis, labels: np.zeros(len(labels)))
    axis = _make_axis(domain=(0.1675, 0.17125), length=100.0)
    axis.transforms.dpi = 100.0
    calls = []

    def formatter(value: float, *, tick_spacing: float | None = None) -> str:
        calls.append((value, tick_spacing))
        return str(value)

    Ticker(axis, tick_format_func=formatter)._get_tick_frac_labels()

    np.testing.assert_allclose(calls, [(value, 0.00125) for value in major_ticks])


def test_tick_label_extents_use_axis_direction_and_font_size(qapp) -> None:
    horizontal = _make_axis(tick_font_size=20.0)
    vertical = _make_axis(tick_font_size=20.0, vertical=True)
    smaller = _make_axis(tick_font_size=10.0)

    horizontal_extent = _tick_label_extents(horizontal, ["16000"])[0]
    vertical_extent = _tick_label_extents(vertical, ["16000"])[0]
    smaller_extent = _tick_label_extents(smaller, ["16000"])[0]

    assert horizontal_extent > vertical_extent
    assert horizontal_extent > smaller_extent


@pytest.mark.parametrize(
    ("length", "expected"),
    [(200.0, False), (100.0, True)],
)
def test_tick_labels_overlap_uses_available_axis_length(monkeypatch, length: float, expected: bool) -> None:
    axis = _make_axis(domain=(0.0, 2.0), length=length)
    values = np.asarray([0.0, 1.0, 2.0])
    labels = ["0", "1", "2"]
    monkeypatch.setattr(axis_module, "_tick_label_extents", lambda _axis, _labels: np.full(3, 60.0))

    assert _tick_labels_overlap(axis, values, labels, axis.domain) is expected


def test_ticker_reduces_density_for_wide_labels(monkeypatch) -> None:
    calls = []

    def locator(_start, _stop, _inches, density):
        calls.append(density)
        step = 1000.0 if density >= 1.0 else 2000.0
        return np.arange(0.0, 16000.0 + step, step)

    monkeypatch.setattr(axis_module, "_get_ticks_talbot", locator)
    monkeypatch.setattr(axis_module, "_tick_label_extents", lambda _axis, labels: np.full(len(labels), 90.0))
    axis = _make_axis()

    fractions, _minor, labels = Ticker(axis)._get_tick_frac_labels()

    assert calls == [2.0, 1.5, 1.125, 0.84375]
    assert len(fractions) == len(labels) == 9
    assert labels == [str(value) for value in range(0, 16001, 2000)]


def test_ticker_keeps_density_when_short_labels_fit(monkeypatch) -> None:
    calls = []
    major_ticks = np.arange(0.0, 16001.0, 1000.0)

    def locator(_start, _stop, _inches, density):
        calls.append(density)
        return major_ticks

    monkeypatch.setattr(axis_module, "_get_ticks_talbot", locator)
    monkeypatch.setattr(axis_module, "_tick_label_extents", lambda _axis, labels: np.full(len(labels), 20.0))

    fractions, _minor, labels = Ticker(_make_axis())._get_tick_frac_labels()

    assert calls == [2.0]
    assert len(fractions) == len(labels) == len(major_ticks)


def test_reduced_ticks_pass_final_spacing_to_formatter(monkeypatch) -> None:
    def locator(_start, _stop, _inches, density):
        step = 1000.0 if density >= 1.0 else 2000.0
        return np.arange(0.0, 16000.0 + step, step)

    monkeypatch.setattr(axis_module, "_get_ticks_talbot", locator)
    monkeypatch.setattr(axis_module, "_tick_label_extents", lambda _axis, labels: np.full(len(labels), 90.0))
    calls = []

    def formatter(value: float, *, tick_spacing: float | None = None) -> str:
        calls.append((value, tick_spacing))
        return f"{value:g}"

    _fractions, _minor, labels = Ticker(_make_axis(), tick_format_func=formatter)._get_tick_frac_labels()

    assert labels == [str(value) for value in range(0, 16001, 2000)]
    assert calls[-len(labels) :] == [(float(value), 2000.0) for value in range(0, 16001, 2000)]


def test_ticker_preserves_reversed_domain_and_masks_outside_ticks(monkeypatch) -> None:
    major_ticks = np.asarray([-5.0, 0.0, 5.0, 10.0, 15.0])
    monkeypatch.setattr(axis_module, "_get_ticks_talbot", lambda *_args: major_ticks)
    monkeypatch.setattr(axis_module, "_tick_label_extents", lambda _axis, labels: np.zeros(len(labels)))

    fractions, minor, labels = Ticker(_make_axis(domain=(10.0, 0.0)))._get_tick_frac_labels()

    np.testing.assert_allclose(fractions, [1.0, 0.5, 0.0])
    assert labels == ["0", "5", "10"]
    assert np.all((minor >= 0.0) & (minor <= 1.0))


def test_ticker_thins_labels_when_lower_density_still_overlaps(monkeypatch) -> None:
    major_ticks = np.arange(0.0, 5.0)
    monkeypatch.setattr(axis_module, "_get_ticks_talbot", lambda *_args: major_ticks)
    monkeypatch.setattr(axis_module, "_tick_label_extents", lambda _axis, labels: np.full(len(labels), 1000.0))
    axis = _make_axis(domain=(0.0, 4.0), length=20.0)

    major, labels = _get_major_ticks(axis, axis_module.default_tick_formatter, axis.domain, 2.0)

    np.testing.assert_allclose(major, major_ticks)
    assert sum(bool(label) for label in labels) == 1
    assert not _tick_labels_overlap(axis, major, labels, axis.domain)
