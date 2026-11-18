"""Tests for input normalization."""

import numpy as np
import pandas as pd
import pytest

from napari_plot.stats._common import dodge_offsets
from napari_plot.stats._data import long_frame, normalize_categorical, parse_orient


@pytest.fixture
def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "day": ["Fri", "Thu", "Fri", "Thu", "Sat"],
            "smoker": ["Yes", "No", "No", "Yes", "No"],
            "bill": [1.0, 2.0, 3.0, np.nan, 5.0],
        }
    )


def test_long_form_with_hue_and_orders(frame: pd.DataFrame) -> None:
    data = normalize_categorical(frame, x="day", y="bill", hue="smoker", order=["Thu", "Fri", "Sat"])
    assert data.orient == "v"
    assert data.labels == ["Thu", "Fri", "Sat"]
    assert data.hue_levels == ["Yes", "No"]
    np.testing.assert_array_equal(data.values("Fri", "No"), [3.0])
    assert data.values("Thu", "Yes").size == 0  # NaN dropped
    assert (data.category_label, data.value_label, data.hue_label) == ("day", "bill", "smoker")


def test_orientation_inferred_from_types(frame: pd.DataFrame) -> None:
    assert normalize_categorical(frame, x="bill", y="day").orient == "h"
    assert normalize_categorical(frame, x="bill").orient == "h"
    assert normalize_categorical(frame, y="bill").labels == [""]
    both_numeric = pd.DataFrame({"a": [1, 1, 2], "b": [0.5, 1.5, 2.5]})
    assert normalize_categorical(both_numeric, x="a", y="b").labels == ["1", "2"]
    assert normalize_categorical(both_numeric, x="a", y="b", orient="y").labels == ["0.5", "1.5", "2.5"]
    with pytest.raises(ValueError, match="orient"):
        parse_orient("diagonal")


def test_hue_equal_to_category_colors_categories(frame: pd.DataFrame) -> None:
    data = normalize_categorical(frame, x="day", y="bill", hue="day")
    assert data.hue_levels is None
    assert data.color_by_category


def test_wide_form_inputs() -> None:
    from_dict = normalize_categorical({"a": [1, 2], "b": [3, 4, 5]})
    assert from_dict.labels == ["a", "b"]
    assert from_dict.values("b").size == 3
    from_array = normalize_categorical(np.arange(6).reshape(3, 2))
    assert from_array.labels == ["0", "1"]
    from_frame = normalize_categorical(pd.DataFrame({"x": [1.0, 2.0], "label": ["p", "q"]}))
    assert from_frame.labels == ["x"]
    assert normalize_categorical([[1, 2], [3]]).labels == ["0", "1"]
    assert normalize_categorical(np.arange(4.0)).all_values.size == 4


def test_long_frame_validation() -> None:
    frame, labels = long_frame({"a": [1, 2]}, x="a", y=np.array([3, 4]), dropna=("x",))
    assert list(frame.columns) == ["x", "y"]
    assert labels == {"x": "a", "y": None}
    with pytest.raises(ValueError, match="no such column"):
        long_frame({"a": [1]}, x="b")
    with pytest.raises(ValueError, match="same length"):
        long_frame(None, x=[1, 2], y=[1])


def test_dodge_offsets() -> None:
    offsets, element = dodge_offsets(2, 0.8, True)
    np.testing.assert_allclose(offsets, [-0.2, 0.2])
    assert element == pytest.approx(0.4)
    offsets, element = dodge_offsets(3, 0.8, False)
    assert element == 0.8
    assert np.all(offsets == 0)
