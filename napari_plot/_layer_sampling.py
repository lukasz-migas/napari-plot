"""Read values from napari image layers for the napari-integration widgets."""

from __future__ import annotations

import typing as ty

import numpy as np

if ty.TYPE_CHECKING:
    from napari.components import Dims
    from napari.layers import Image


def layer_axes(layer: Image, dims: Dims, world_axes: ty.Iterable[int]) -> list[int]:
    """Map viewer (world) axes to the matching axes of ``layer``.

    Layers with fewer dimensions than the viewer are aligned to its last axes, so leading world axes have no
    matching layer axis and are dropped.
    """
    offset = dims.ndim - layer.ndim
    return [axis - offset for axis in world_axes if axis - offset >= 0]


def world_to_layer(layer: Image, world: np.ndarray) -> np.ndarray:
    """Convert (N, D) world coordinates to the layer's data coordinates."""
    world = np.atleast_2d(np.asarray(world, dtype=float))[:, -layer.ndim :]
    return np.atleast_2d(layer._data_to_world.inverse(world))


def image_plane(layer: Image, dims: Dims) -> tuple[np.ndarray, list[int]]:
    """Return the 2D plane of ``layer`` displayed at the current dims point.

    The plane is taken from ``layer.data`` (not napari's slice cache), so it is full resolution and works for
    NumPy and dask arrays. RGB(A) planes are averaged over their color channels.

    Returns
    -------
    plane : np.ndarray
        Float array with one value per displayed pixel.
    displayed : list of int
        The layer axes that map onto the plane's rows and columns.
    """
    if layer.multiscale:
        raise ValueError("Multiscale images are not supported.")
    displayed = layer_axes(layer, dims, sorted(dims.displayed))
    point = world_to_layer(layer, np.asarray(dims.point))[0]
    shape = layer.data.shape
    index: list[int | slice] = []
    for axis in range(layer.ndim):
        if axis in displayed:
            index.append(slice(None))
        else:
            index.append(int(np.clip(np.round(point[axis]), 0, shape[axis] - 1)))
    plane = np.asarray(layer.data[tuple(index)], dtype=float)
    if layer.rgb:
        plane = plane[..., :3].mean(axis=-1)
    return plane, displayed


def sample_bilinear(plane: np.ndarray, coords: np.ndarray) -> np.ndarray:
    """Sample a 2D array at fractional (row, column) positions.

    Positions outside the array return NaN.
    """
    coords = np.asarray(coords, dtype=float).reshape(-1, 2)
    rows, cols = coords[:, 0], coords[:, 1]
    height, width = plane.shape
    values = np.full(len(coords), np.nan)
    inside = (rows >= 0) & (cols >= 0) & (rows <= height - 1) & (cols <= width - 1)
    if not inside.any():
        return values
    r, c = rows[inside], cols[inside]
    r0 = np.floor(r).astype(int)
    c0 = np.floor(c).astype(int)
    r1 = np.minimum(r0 + 1, height - 1)
    c1 = np.minimum(c0 + 1, width - 1)
    dr, dc = r - r0, c - c0
    top = plane[r0, c0] * (1 - dc) + plane[r0, c1] * dc
    bottom = plane[r1, c0] * (1 - dc) + plane[r1, c1] * dc
    values[inside] = top * (1 - dr) + bottom * dr
    return values


def resample_path(vertices: np.ndarray, step: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """Return evenly spaced points along a polyline and their distance from its start.

    Parameters
    ----------
    vertices : np.ndarray
        (N, D) polyline vertices, N >= 2.
    step : float
        Approximate spacing between returned points, in the units of ``vertices``.
    """
    vertices = np.asarray(vertices, dtype=float)
    segment = np.linalg.norm(np.diff(vertices, axis=0), axis=1)
    distance = np.concatenate(([0.0], np.cumsum(segment)))
    total = distance[-1]
    if total == 0:
        return vertices[:1], np.zeros(1)
    n_samples = max(int(np.ceil(total / step)) + 1, 2)
    samples = np.linspace(0, total, n_samples)
    points = np.column_stack([np.interp(samples, distance, vertices[:, axis]) for axis in range(vertices.shape[1])])
    return points, samples


SERIES_COLORS = ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#17becf")


def layer_color(layer: Image, index: int = 0) -> np.ndarray | str:
    """Return the top color of an image layer's colormap.

    RGB and gray colormaps fall back to ``SERIES_COLORS[index]``, since white or black lines would vanish on one of
    the plot themes.
    """
    fallback = SERIES_COLORS[index % len(SERIES_COLORS)]
    if layer.rgb:
        return fallback
    color = np.asarray(layer.colormap.colors[-1], dtype=float)
    if np.ptp(color[:3]) < 1e-3:
        return fallback
    return color
