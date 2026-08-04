"""Tests for the Text layer model."""

from __future__ import annotations

import numpy as np
import pytest

from napari_plot.layers import Text


def test_text_empty() -> None:
    """An empty layer retains valid two-dimensional arrays."""
    layer = Text()

    assert layer.data.shape == (0, 2)
    assert layer.text.shape == (0,)
    assert layer.ndim == 2


def test_text_layer_and_per_label_styles() -> None:
    """Typography is layer-wide while color, rotation, and offset are per-label."""
    layer = Text(
        [[1, 2], [3, 4]],
        ["first", "second"],
        size=20,
        color=["red", "blue"],
        alignment="right",
        vertical_alignment="bottom",
        rotation=[0, 45],
        offset=(1, -1),
    )

    np.testing.assert_array_equal(layer.text, ["first", "second"])
    assert layer.size == 20
    assert layer.alignment == "right"
    assert layer.vertical_alignment == "bottom"
    np.testing.assert_array_equal(layer.rotation, [0, 45])
    np.testing.assert_array_equal(layer.offset, [[1, -1], [1, -1]])
    np.testing.assert_array_equal(layer.color[0], [1, 0, 0, 1])
    np.testing.assert_array_equal(layer.color[1], [0, 0, 1, 1])


def test_text_string_broadcasts() -> None:
    """One string can label every supplied coordinate."""
    layer = Text([[1, 2], [3, 4]], "same")

    np.testing.assert_array_equal(layer.text, ["same", "same"])


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"size": [10]}, "size"),
        ({"size": 0}, "greater than zero"),
        ({"color": ["red", "blue", "green"]}, "color"),
        ({"alignment": "middle"}, "alignment"),
        ({"vertical_alignment": "left"}, "vertical_alignment"),
        ({"rotation": [0]}, "rotation"),
        ({"offset": [[0, 0]]}, "offset"),
    ],
)
def test_text_rejects_invalid_styles(kwargs: dict, match: str) -> None:
    """Styles must use valid scalar values or correctly sized vectors."""
    with pytest.raises(ValueError, match=match):
        Text([[1, 2], [3, 4]], ["a", "b"], **kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"alignment": ["left", "right"]},
        {"vertical_alignment": ["top", "bottom"]},
    ],
)
def test_text_rejects_per_label_alignment(kwargs: dict) -> None:
    """One native Text visual requires layer-wide alignment values."""
    with pytest.raises(TypeError, match="must be a string"):
        Text([[1, 2], [3, 4]], ["a", "b"], **kwargs)


@pytest.mark.parametrize("data", [[[1, 2, 3]], [1, 2], [[1], [2]]])
def test_text_rejects_invalid_coordinates(data) -> None:
    """Coordinates must be a two-column array."""
    with pytest.raises(ValueError, match="N, 2"):
        Text(data, "label")


def test_text_property_events() -> None:
    """Changing label properties emits their dedicated events."""
    layer = Text([[1, 2]], "before")
    received: list[str] = []
    layer.events.text.connect(lambda event: received.append(event.type))
    layer.events.size.connect(lambda event: received.append(event.type))

    layer.text = "after"
    layer.size = 18

    assert received == ["text", "size"]
    np.testing.assert_array_equal(layer.text, ["after"])
    assert layer.size == 18


def test_text_data_resize_preserves_and_extends_attributes() -> None:
    """Count changes truncate or extend associated label properties."""
    layer = Text(
        [[1, 2], [3, 4]],
        ["a", "b"],
        size=20,
        alignment="right",
    )

    layer.data = [[1, 2], [3, 4], [5, 6]]
    np.testing.assert_array_equal(layer.text, ["a", "b", ""])
    assert layer.size == 20
    assert layer.alignment == "right"

    layer.data = [[1, 2]]
    np.testing.assert_array_equal(layer.text, ["a"])
    assert layer.size == 20


def test_text_xy_properties() -> None:
    """Coordinate convenience properties update the underlying data."""
    layer = Text([[1, 2], [3, 4]], ["a", "b"])

    layer.x = [5, 6]
    layer.y = [7, 8]

    np.testing.assert_array_equal(layer.data, [[5, 7], [6, 8]])
    assert np.all(layer.extent.data[0] < [7, 5])
    assert np.all(layer.extent.data[1] > [8, 6])


@pytest.mark.parametrize(
    ("alignment", "expected_direction"),
    [("left", "right"), ("center", "both"), ("right", "left")],
)
def test_text_extent_uses_horizontal_alignment(
    alignment: str,
    expected_direction: str,
) -> None:
    """Horizontal alignment expands the extent on the rendered side."""
    layer = Text([[1, 2]], "label", size=20, alignment=alignment)
    x_min, x_max = layer.extent.data[:, 1]

    assert bool(x_min < 1) is (expected_direction in {"left", "both"})
    assert bool(x_max > 1) is (expected_direction in {"right", "both"})


@pytest.mark.parametrize(
    ("alignment", "expected_direction"),
    [
        ("top", "above"),
        ("center", "both"),
        ("baseline", "both"),
        ("bottom", "below"),
    ],
)
def test_text_extent_uses_vertical_alignment(
    alignment: str,
    expected_direction: str,
) -> None:
    """Vertical alignment expands the extent on the rendered side."""
    layer = Text([[1, 2]], "label", size=20, vertical_alignment=alignment)
    y_min, y_max = layer.extent.data[:, 0]

    assert bool(y_min < 2) is (expected_direction in {"below", "both"})
    assert bool(y_max > 2) is (expected_direction in {"above", "both"})


def test_text_extent_includes_bottom_aligned_troughs() -> None:
    """Bottom-aligned labels at the lower data limit extend that limit."""
    layer = Text(
        [[0.25, 1], [0.75, -1], [1.25, 1], [1.75, -1]],
        ["peak", "trough", "peak", "trough"],
        size=18,
        alignment="center",
        vertical_alignment="bottom",
        rotation=[0, -10, 10, 0],
        offset=(0, 0.05),
    )

    assert layer.extent.data[0, 0] < -1


def test_text_extent_uses_offset_text_and_font_size() -> None:
    """Offsets move label bounds and larger or longer text expands them."""
    small = Text([[1, 2]], "a", size=10, offset=(3, 4))
    large = Text([[1, 2]], "long label", size=20, offset=(3, 4))

    small_height, small_width = np.ptp(small.extent.data, axis=0)
    large_height, large_width = np.ptp(large.extent.data, axis=0)

    assert np.mean(small.extent.data[:, 0]) == pytest.approx(6)
    assert np.mean(small.extent.data[:, 1]) == pytest.approx(4)
    assert large_height > small_height
    assert large_width > small_width


def test_text_extent_uses_rotation() -> None:
    """A quarter turn swaps the estimated label width and height."""
    horizontal = Text([[1, 2]], "label", alignment="left", vertical_alignment="bottom")
    vertical = Text(
        [[1, 2]],
        "label",
        alignment="left",
        vertical_alignment="bottom",
        rotation=90,
    )

    horizontal_height, horizontal_width = np.ptp(horizontal.extent.data, axis=0)
    vertical_height, vertical_width = np.ptp(vertical.extent.data, axis=0)

    assert vertical_height == pytest.approx(horizontal_width)
    assert vertical_width == pytest.approx(horizontal_height)


def test_text_extent_cache_is_cleared_by_style_changes() -> None:
    """Style updates are reflected after the extent has been cached."""
    layer = Text([[1, 2]], "a", size=10, alignment="left")
    initial_extent = layer.extent.data.copy()

    layer.text = "long label"
    layer.size = 20
    layer.alignment = "right"

    assert layer.extent.data[0, 1] < initial_extent[0, 1]
    assert layer.extent.data[1, 1] == pytest.approx(1)
