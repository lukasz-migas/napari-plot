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


def test_text_scalar_and_array_styles() -> None:
    """Scalar values broadcast while arrays remain per-label."""
    layer = Text(
        [[1, 2], [3, 4]],
        ["first", "second"],
        size=[10, 20],
        color=["red", "blue"],
        alignment=["left", "right"],
        vertical_alignment="bottom",
        rotation=[0, 45],
        offset=(1, -1),
    )

    np.testing.assert_array_equal(layer.text, ["first", "second"])
    np.testing.assert_array_equal(layer.size, [10, 20])
    np.testing.assert_array_equal(layer.alignment, ["left", "right"])
    np.testing.assert_array_equal(layer.vertical_alignment, ["bottom", "bottom"])
    np.testing.assert_array_equal(layer.rotation, [0, 45])
    np.testing.assert_array_equal(layer.offset, [[1, -1], [1, -1]])
    np.testing.assert_array_equal(layer.color[0], [1, 0, 0, 1])
    np.testing.assert_array_equal(layer.color[1], [0, 0, 1, 1])


def test_text_string_broadcasts() -> None:
    """One string can label every supplied coordinate."""
    layer = Text([[1, 2], [3, 4]], "same")

    np.testing.assert_array_equal(layer.text, ["same", "same"])


def test_text_scaling_defaults_on_and_emits_event() -> None:
    """Zoom scaling is enabled by default and remains event-driven."""
    layer = Text([[1, 2]], "label")
    received: list[bool] = []
    layer.events.scaling.connect(lambda event: received.append(event.value))

    assert layer.scaling is True
    layer.scaling = False

    assert layer.scaling is False
    assert received == [False]


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
    """Per-label values must match the coordinate count and valid choices."""
    with pytest.raises(ValueError, match=match):
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
    np.testing.assert_array_equal(layer.size, [18])


def test_text_data_resize_preserves_and_extends_attributes() -> None:
    """Count changes truncate or extend associated label properties."""
    layer = Text(
        [[1, 2], [3, 4]],
        ["a", "b"],
        size=[10, 20],
        alignment=["left", "right"],
    )

    layer.data = [[1, 2], [3, 4], [5, 6]]
    np.testing.assert_array_equal(layer.text, ["a", "b", ""])
    np.testing.assert_array_equal(layer.size, [10, 20, 20])
    np.testing.assert_array_equal(layer.alignment, ["left", "right", "right"])

    layer.data = [[1, 2]]
    np.testing.assert_array_equal(layer.text, ["a"])
    np.testing.assert_array_equal(layer.size, [10])


def test_text_xy_properties() -> None:
    """Coordinate convenience properties update the underlying data."""
    layer = Text([[1, 2], [3, 4]], ["a", "b"])

    layer.x = [5, 6]
    layer.y = [7, 8]

    np.testing.assert_array_equal(layer.data, [[5, 7], [6, 8]])
    np.testing.assert_array_equal(layer.extent.data, [[7, 5], [8, 6]])
