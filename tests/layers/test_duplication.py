"""Tests for duplicating custom napari-plot layers."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pytest
from napari.components import LayerList
from napari.layers._layer_actions import _duplicate_layer

from napari_plot.layers import Centroids, InfLine, Line, MultiLine, Region, Scatter, Text
from napari_plot.layers.base import LayerMixin


@pytest.mark.parametrize(
    ("factory", "state_keys"),
    [
        pytest.param(
            lambda: Line([[0, 1], [1, 2]], color="red", width=3, method="agg"),
            ("color", "width", "method"),
            id="line",
        ),
        pytest.param(
            lambda: InfLine(
                [1, 2],
                orientation=["horizontal", "vertical"],
                color=["red", "blue"],
                width=3,
                z_index=[2, 1],
            ),
            ("orientation", "color", "width", "z_index"),
            id="infline",
        ),
        pytest.param(
            lambda: Region(
                [[1, 2], [3, 4]],
                orientation=["horizontal", "vertical"],
                color=["red", "blue"],
                z_index=[2, 1],
            ),
            ("orientation", "color", "z_index"),
            id="region",
        ),
        pytest.param(
            lambda: MultiLine(
                (np.array([0, 1]), np.array([1, 2])),
                color="red",
                width=3,
                method="agg",
            ),
            ("color", "width", "method"),
            id="multiline",
        ),
        pytest.param(
            lambda: Centroids(
                [[0, 1]],
                orientation="horizontal",
                color="red",
                width=3,
                method="agg",
            ),
            ("orientation", "color", "width", "method"),
            id="centroids",
        ),
        pytest.param(
            lambda: Scatter([[0, 1]], face_color="red", symbol="square", scaling=False),
            ("face_color", "symbol", "scaling"),
            id="scatter",
        ),
        pytest.param(
            lambda: Text(
                [[1, 2], [3, 4]],
                ["first", "second"],
                size=[10, 20],
                color=["red", "blue"],
                alignment=["left", "right"],
                vertical_alignment=["top", "bottom"],
                rotation=[0, 15],
                offset=[[1, 0], [0, 1]],
                font_face="Arial",
                bold=True,
            ),
            (
                "text",
                "size",
                "color",
                "alignment",
                "vertical_alignment",
                "rotation",
                "offset",
                "font_face",
                "bold",
                "italic",
                "scaling",
            ),
            id="text",
        ),
    ],
)
def test_native_duplicate_action_preserves_custom_layer_state(
    factory: Callable[[], LayerMixin], state_keys: tuple[str, ...]
) -> None:
    """Napari's native duplicate action should recreate every custom layer."""
    layer = factory()
    layer.name = "source"
    layer_list = LayerList([layer])
    layer_list.selection.add(layer)
    source_state = layer._get_state()

    _duplicate_layer(layer_list)

    duplicate = layer_list[1]
    duplicate_state = duplicate._get_state()
    assert type(duplicate) is type(layer)
    assert duplicate.name == "source copy"
    np.testing.assert_equal(duplicate.data, layer.data)
    for key in state_keys:
        np.testing.assert_equal(duplicate_state[key], source_state[key])
