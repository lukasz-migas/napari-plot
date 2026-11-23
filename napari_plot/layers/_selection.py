"""Geometry tests for polygon selection in layer coordinates."""

import numpy as np
from numpy.typing import ArrayLike, NDArray


def points_in_polygon(points: ArrayLike, vertices: ArrayLike, *, include_boundary: bool = True) -> NDArray[np.bool_]:
    """Test which points lie inside a polygon using the even-odd rule."""
    points = np.asarray(points, dtype=float)
    vertices = np.asarray(vertices, dtype=float)
    inside = np.zeros(points.shape[:-1], dtype=bool)
    if len(vertices) < 3:
        return inside

    x, y = np.moveaxis(points, -1, 0)
    boundary = np.zeros_like(inside)
    for start, end in zip(vertices, np.roll(vertices, -1, axis=0), strict=True):
        dx, dy = end - start
        if dy:
            crosses = (start[1] < y) != (end[1] < y)
            hit = start[0] + (y - start[1]) * dx / dy
            inside ^= crosses & (x < hit)
        if include_boundary:
            offset = points - start
            cross = dx * offset[..., 1] - dy * offset[..., 0]
            tolerance = np.finfo(float).eps * 8 * (abs(dx * offset[..., 1]) + abs(dy * offset[..., 0]))
            in_bounds = np.all((points >= np.minimum(start, end)) & (points <= np.maximum(start, end)), axis=-1)
            boundary |= (abs(cross) <= tolerance) & in_bounds
    return (inside | boundary) & np.all(np.isfinite(points), axis=-1)


def segments_intersect_polygon(starts: ArrayLike, ends: ArrayLike, vertices: ArrayLike) -> NDArray[np.bool_]:
    """Test which segments touch or pass through the polygon."""
    starts = np.asarray(starts, dtype=float)
    ends = np.asarray(ends, dtype=float)
    vertices = np.asarray(vertices, dtype=float)
    hits = points_in_polygon(starts, vertices) | points_in_polygon(ends, vertices)
    if len(vertices) < 3:
        return hits

    low, high = np.minimum(starts, ends), np.maximum(starts, ends)
    delta = ends - starts
    for start, end in zip(vertices, np.roll(vertices, -1, axis=0), strict=True):
        overlap = np.all((low <= np.maximum(start, end)) & (high >= np.minimum(start, end)), axis=-1)
        start_side = _cross(delta, start - starts)
        end_side = _cross(delta, end - starts)
        side_of_edge = _cross(end - start, starts - start)
        other_side = _cross(end - start, ends - start)
        hits |= overlap & (start_side * end_side <= 0) & (side_of_edge * other_side <= 0)
    return hits & np.all(np.isfinite(starts) & np.isfinite(ends), axis=-1)


def _cross(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    return first[..., 0] * second[..., 1] - first[..., 1] * second[..., 0]
