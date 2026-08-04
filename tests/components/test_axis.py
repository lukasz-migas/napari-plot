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


def test_categories_activate_categorical_scales() -> None:
    axis = Axis(x_categories=["first", "second"], y_categories=("low", "high"))

    assert axis.x_categories == ("first", "second")
    assert axis.y_categories == ("low", "high")
    assert axis.x_scale is AxisScale.CATEGORICAL
    assert axis.y_scale is AxisScale.CATEGORICAL


def test_clearing_categories_restores_linear_scale() -> None:
    axis = Axis(x_categories=["first", "second"])

    axis.x_categories = None

    assert axis.x_categories is None
    assert axis.x_scale is AxisScale.LINEAR


def test_selecting_numeric_scale_clears_categories() -> None:
    axis = Axis(x_categories=["first", "second"])

    axis.x_scale = "log"

    assert axis.x_categories is None
    assert axis.x_scale is AxisScale.LOG


def test_categorical_scale_requires_categories() -> None:
    with pytest.raises(ValueError, match="x_categories must be provided"):
        Axis(x_scale="categorical")

    axis = Axis()
    with pytest.raises(ValueError, match="x_categories must be provided"):
        axis.x_scale = "categorical"


@pytest.mark.parametrize("categories", [[], "label", ["label", 1]])
def test_categories_require_non_empty_string_sequence(categories) -> None:
    with pytest.raises((TypeError, ValueError)):
        Axis(x_categories=categories)


def test_log_axis_values_round_trip() -> None:
    values = np.asarray([0.1, 1.0, 10.0, 1000.0])

    displayed = transform_axis_values(values, AxisScale.LOG)
    restored = transform_axis_values(displayed, AxisScale.LOG, inverse=True)

    np.testing.assert_allclose(displayed, [-1.0, 0.0, 1.0, 3.0])
    np.testing.assert_allclose(restored, values)


def test_categorical_axis_values_are_not_transformed() -> None:
    values = np.asarray([-0.5, 0.0, 1.5, 10.0])

    assert transform_axis_values(values, AxisScale.CATEGORICAL) is values
    assert transform_axis_values(values, AxisScale.CATEGORICAL, inverse=True) is values


def test_log_axis_rejects_non_positive_limits() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        transform_axis_values(0.0, AxisScale.LOG)
