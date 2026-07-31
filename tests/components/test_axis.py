"""Tests for the axis model and coordinate transforms."""

import numpy as np
import pytest

from napari_plot.components.axis import Axis, AxisScale, transform_axis_values


def test_axis_scales_default_to_linear() -> None:
    axis = Axis()

    assert axis.x_scale is AxisScale.LINEAR
    assert axis.y_scale is AxisScale.LINEAR


def test_axis_scales_accept_log_values() -> None:
    axis = Axis(x_scale="log", y_scale=AxisScale.LOG)

    assert axis.x_scale is AxisScale.LOG
    assert axis.y_scale is AxisScale.LOG


def test_log_axis_values_round_trip() -> None:
    values = np.asarray([0.1, 1.0, 10.0, 1000.0])

    displayed = transform_axis_values(values, AxisScale.LOG)
    restored = transform_axis_values(displayed, AxisScale.LOG, inverse=True)

    np.testing.assert_allclose(displayed, [-1.0, 0.0, 1.0, 3.0])
    np.testing.assert_allclose(restored, values)


def test_log_axis_rejects_non_positive_limits() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        transform_axis_values(0.0, AxisScale.LOG)
