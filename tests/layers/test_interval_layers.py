"""Test filled bands and error intervals through the plotting API."""

import numpy as np
import pytest

from napari_plot.components.viewer_model import ViewerModel
from napari_plot.layers import Band, ErrorBar


@pytest.mark.parametrize("reverse", [False, True])
def test_band_crossing_and_gap(reverse: bool) -> None:
    """Split crossing triangles and leave NaN gaps unfilled in either x order."""
    data = np.array([[0, 1, -1], [2, -1, 1], [3, np.nan, 20], [4, 2, 1], [5, 3, 1]])
    layer = Band(data[::-1] if reverse else data)
    triangles = layer._triangles()
    assert triangles.shape == (4, 3, 2)
    crossing = triangles[np.max(triangles[..., 0], axis=1) <= 2]
    assert np.all(np.any(np.all(crossing == [1, 0], axis=2), axis=1))
    np.testing.assert_array_equal(layer.extent.data, [[-1, 0], [3, 5]])
    assert layer._get_x_region_extent(0.5, 1.5) == (-0.5, 0.5)
    assert layer._get_x_region_extent(2.1, 3.9) == (None, None)


def test_fill_between_updates_both_bounds() -> None:
    """Use scalar bounds and update autoscaling after replacing band data."""
    viewer = ViewerModel()
    band = viewer.fill_between([1, 2], [-1, 1], name="Baseline")
    np.testing.assert_array_equal(band.data, [[1, -1, 0], [2, 1, 0]])

    band.data = [[1, 2, 3], [4, 5, 6]]
    assert viewer.camera.extent == pytest.approx((1, 4, 2, 6))
    with pytest.raises(ValueError, match="strictly increasing or decreasing"):
        band.data = [[1, 2, 3], [1, 3, 4]]
    np.testing.assert_array_equal(band.data, [[1, 2, 3], [4, 5, 6]])
    band.data = []
    assert band.data.shape == (0, 3)
    assert not len(band._triangles())


def test_errorbar_offsets_and_extent() -> None:
    """Normalize both kinds of offsets and use interval endpoints for extents."""
    viewer = ViewerModel()
    layer = viewer.errorbar([10, 20], [2, 4], xerr=0.5, yerr=[[1, 2], [3, 4]])
    assert isinstance(layer, ErrorBar)
    np.testing.assert_array_equal(layer.data, [[10, 2, 0.5, 0.5, 1, 3], [20, 4, 0.5, 0.5, 2, 4]])
    np.testing.assert_array_equal(
        layer._segments(), [[[9.5, 2], [10.5, 2]], [[10, 1], [10, 5]], [[19.5, 4], [20.5, 4]], [[20, 2], [20, 8]]]
    )
    assert viewer.camera.extent == pytest.approx((9.5, 20.5, 1, 8))
    assert layer._get_x_region_extent(9.6, 10.4) == (1, 5)

    updated = viewer.errorbar([1, 2], [3, 4], yerr=[2, np.nan])
    layer.data = updated.data
    np.testing.assert_array_equal(layer._segments(), [[[1, 1], [1, 5]]])
    assert viewer.camera.extent == pytest.approx((1, 1, 1, 5))
    layer.data = None
    assert layer.data.shape == (0, 6)
    assert np.isnan(layer.extent.data).all()


def test_errorbar_invalid_offsets() -> None:
    """Reject mismatched arrays, negative offsets, and half-missing intervals."""
    viewer = ViewerModel()
    with pytest.raises(ValueError, match="Error offsets must be"):
        viewer.errorbar([1, 2], [3, 4], xerr=[1])
    with pytest.raises(ValueError, match="nonnegative"):
        viewer.errorbar([1], [2], xerr=-1)
    with pytest.raises(ValueError, match="both NaN"):
        viewer.errorbar([1], [2], yerr=[[np.nan], [1]])


def test_interval_layers_update_legend() -> None:
    """Synchronize entries when interval layers change color or visibility."""
    viewer = ViewerModel()
    viewer.set_legend_from_layers(sync=True)
    band = viewer.add_band([[0, 0, 1], [1, 0, 2]], name="Variation")
    errors = viewer.errorbar([1], [2], yerr=1, name="Intervals")

    assert [entry.label for entry in viewer.legend.entries] == ["Variation", "Intervals"]
    band.fill_color = "red"
    errors.color = "cyan"
    np.testing.assert_allclose([entry.color for entry in viewer.legend.entries], [[1, 0, 0, 1], [0, 1, 1, 1]])
    band.visible = False
    assert [entry.label for entry in viewer.legend.entries] == ["Intervals"]
