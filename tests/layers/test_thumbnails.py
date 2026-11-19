"""Layer-list thumbnail regression tests."""

from __future__ import annotations

from unittest.mock import PropertyMock

import numpy as np
import pytest
from napari._qt.containers.qt_layer_model import ThumbnailRole
from napari.components import LayerList
from pytestqt.qtbot import QtBot

from napari_plot._qt.qt_layer_list import QtLayerList
from napari_plot.layers import (
    Areas,
    Band,
    Bar,
    Centroids,
    ErrorBar,
    InfLine,
    Line,
    MultiLine,
    Rectangles,
    Region,
    Scatter,
    Text,
)


def test_empty_layers_have_distinct_thumbnails() -> None:
    """Even empty and initially hidden layers have identifiable previews."""
    layer_types = (Areas, Band, Bar, Centroids, ErrorBar, InfLine, Line, MultiLine, Rectangles, Region, Scatter, Text)
    silhouettes = set()
    for layer_type in layer_types:
        layer = layer_type(None, visible=False)
        assert layer.thumbnail.shape == layer._thumbnail_shape
        assert layer.thumbnail.dtype == np.uint8
        mask = layer.thumbnail[..., :3].any(axis=-1)
        assert mask.any()
        assert not mask.all()
        silhouettes.add(mask.tobytes())

    assert len(silhouettes) == len(layer_types)


def test_bar_thumbnail_tracks_style_changes() -> None:
    """Color, orientation and opacity update the published image immediately."""
    layer = Bar([1, 2])
    layer.fill_color = "red"
    vertical = layer.thumbnail.copy()
    assert vertical[..., 0].max() == 255
    assert not vertical[..., 1:3].any()

    layer.orientation = "horizontal"
    np.testing.assert_array_equal(layer.thumbnail, vertical.transpose(1, 0, 2)[:, ::-1])
    layer.opacity = 0.5
    assert 0 < layer.thumbnail[..., 0].max() < 255
    layer.opacity = 0
    assert not layer.thumbnail[..., :3].any()


def test_scatter_thumbnail_avoids_view_and_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Recoloring a scatter thumbnail needs only representative colors."""
    layer = Scatter([[0, 0], [1, 1]])
    for attr in ("_view_data", "_extent_data"):
        monkeypatch.setattr(Scatter, attr, PropertyMock(side_effect=AssertionError(attr)))

    layer.face_color = "lime"
    thumbnail = layer.thumbnail.copy()
    assert thumbnail[..., 1].max() == 255
    assert not thumbnail[..., [0, 2]].any()
    layer._update_thumbnail()
    np.testing.assert_array_equal(layer.thumbnail, thumbnail)


def test_layer_list_receives_thumbnail_change(qtbot: QtBot) -> None:
    """The layer-list model exposes the new image after a style edit."""
    layer = Line([[0, 0], [1, 1]])
    view = QtLayerList(LayerList([layer]))
    qtbot.addWidget(view)
    model = view.model()
    index = model.index(0, 0)
    before = index.data(ThumbnailRole)

    with qtbot.waitSignal(
        model.dataChanged, timeout=1000, check_params_cb=lambda _first, _last, roles: ThumbnailRole in roles
    ):
        layer.color = "red"
    assert index.data(ThumbnailRole) != before


def test_thumbnail_blocking_is_nested_and_exception_safe() -> None:
    """Restore the outer block even when its inner block fails."""
    layer = Line([[0, 0], [1, 1]])
    thumbnail = layer.thumbnail.copy()
    with layer.block_thumbnail_update():
        with pytest.raises(ValueError, match="interrupted"):
            with layer.block_thumbnail_update():
                raise ValueError("interrupted")
        layer.color = "red"
        np.testing.assert_array_equal(layer.thumbnail, thumbnail)

    layer.opacity = 0.5
    assert layer.thumbnail[..., 0].any()
    assert not layer.thumbnail[..., 1:3].any()
