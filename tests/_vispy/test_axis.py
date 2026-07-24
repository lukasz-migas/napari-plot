"""Tests for Vispy axis tick formatting."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

import napari_plot._vispy.components.axis as axis_module
from napari_plot._vispy.components.axis import Ticker, _format_ticks


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
    axis = SimpleNamespace(
        domain=np.asarray([0.1675, 0.17125]),
        pos=np.asarray([[0.0, 0.0], [100.0, 0.0]]),
        scale_type="linear",
        transforms=SimpleNamespace(dpi=100),
        _stop_at_major=(False, False),
    )
    calls = []

    def formatter(value: float, *, tick_spacing: float | None = None) -> str:
        calls.append((value, tick_spacing))
        return str(value)

    Ticker(axis, tick_format_func=formatter)._get_tick_frac_labels()

    np.testing.assert_allclose(calls, [(value, 0.00125) for value in major_ticks])
