import numpy as np
from napari.layers import Layer

from napari_plot import layers
from napari_plot.utils.utilities import find_nearest_index, get_min_max


def get_x_region_extent(x_min: float, x_max: float, layer: Layer) -> tuple[float | None, ...]:
    """Get extent for specified range"""
    if not layer.visible:
        return None, None
    if layer.ndim != 2:
        return None, None
    if hasattr(layer, "_get_x_region_extent"):
        return layer._get_x_region_extent(x_min, x_max)
    return None, None


def get_layers_x_region_extent(x_min: float, x_max: float, layer_list) -> tuple[float | None, ...]:
    """Get layer extents"""
    extents = []
    for layer in layer_list:
        y_min, y_max = get_x_region_extent(x_min, x_max, layer)
        if y_min is None:
            continue
        extents.extend([y_min, y_max])
    if extents:
        extents = np.asarray(extents)
        return get_min_max(extents)
    return None, None


def get_y_region_extent(x_min: float, x_max: float, layer: Layer) -> tuple[float | None, ...]:
    """Get extent for specified range"""
    if not layer.visible:
        return None, None
    if layer.ndim != 2:
        return None, None
    if isinstance(layer, (layers.Line, layers.Centroids)):
        idx_min, idx_max = find_nearest_index(layer.data[:, 1], [x_min, x_max])
        if idx_min == idx_max:
            idx_max += 1
            if idx_max > len(layer.data):
                return None, None
        try:
            return get_min_max(layer.data[idx_min:idx_max, 1])
        except ValueError:
            return None, None
    if isinstance(layer, layers.Scatter):
        idx_min, idx_max = find_nearest_index(layer.data[:, 0], [x_min, x_max])
        if idx_min == idx_max:
            idx_max += 1
            if idx_max > len(layer.data):
                return None, None
        try:
            return get_min_max(layer.data[idx_min:idx_max, 1])
        except ValueError:
            return None, None
    return None, None


def get_layers_y_region_extent(y_min: float, y_max: float, layer_list) -> tuple[float | None, ...]:
    """Get layer extents"""
    extents = []
    for layer in layer_list:
        x_min, x_max = get_y_region_extent(y_min, y_max, layer)
        if x_min is None:
            continue
        extents.extend([x_min, x_max])
    if extents:
        extents = np.asarray(extents)
        return get_min_max(extents)
    return None, None


def get_region_extent(axis: int, lo: float, hi: float, layer: Layer) -> tuple[float | None, float | None]:
    """Extent along the other axis of a layer's data whose ``axis`` (0 = x, 1 = y) coordinate is in ``[lo, hi]``."""
    if not layer.visible or layer.ndim != 2:
        return None, None
    if hasattr(layer, "_get_region_extent"):
        return layer._get_region_extent(axis, lo, hi)
    if axis == 0 and hasattr(layer, "_get_x_region_extent"):
        return layer._get_x_region_extent(lo, hi)
    return None, None


def get_layers_region_extent(axis: int, lo: float, hi: float, layer_list) -> tuple[float | None, float | None]:
    """Extent along the other axis of the data of every layer whose ``axis`` coordinate is in ``[lo, hi]``."""
    extents = []
    for layer in layer_list:
        vmin, vmax = get_region_extent(axis, lo, hi, layer)
        if vmin is not None and vmax is not None:
            extents.extend([vmin, vmax])
    return (float(min(extents)), float(max(extents))) if extents else (None, None)


def points_region_extent(
    positions: np.ndarray, values: np.ndarray, lo: float, hi: float
) -> tuple[float | None, float | None]:
    """Range of the finite ``values`` whose ``positions`` are in ``[lo, hi]`` (in any order)."""
    mask = (positions >= lo) & (positions <= hi) & np.isfinite(values)
    if not mask.any():
        return None, None
    selected = values[mask]
    return float(selected.min()), float(selected.max())


def get_range_extent(full_min, full_max, range_min, range_max, min_val: float | None = None) -> tuple[float, float]:
    """Get tuple of specified range"""
    if range_min is None:
        range_min = full_min
    if range_max is None:
        range_max = full_max
    if min_val is None:
        min_val = range_min
    return get_min_max([range_min, range_max, min_val])
