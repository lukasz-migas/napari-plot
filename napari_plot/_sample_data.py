"""Sample data for trying the napari-plot widgets inside napari."""

from __future__ import annotations

import typing as ty

import numpy as np

__all__ = ["make_labeled_blobs", "make_spot_time_lapse"]

LayerDataTuple = tuple[ty.Any, dict[str, ty.Any], str]


def make_spot_time_lapse() -> list[LayerDataTuple]:
    """Time-lapse of drifting, bleaching Gaussian spots with their tracked centers and a profile line.

    Use it with the line profile (draw in 'Profile line'), cursor profile (time axis), histogram and features
    widgets ('Spot centers' has per-point intensity, size and speed).
    """
    rng = np.random.default_rng(42)
    n_frames, height, width, n_spots = 24, 128, 160, 6
    start = rng.uniform((20, 20), (height - 20, width - 20), size=(n_spots, 2))
    velocity = rng.uniform(-1.5, 1.5, size=(n_spots, 2))
    amplitude = rng.uniform(0.5, 1.0, size=n_spots)
    sigma = rng.uniform(3, 7, size=n_spots)
    rows, cols = np.mgrid[0:height, 0:width]

    stack = np.empty((n_frames, height, width), dtype=np.float32)
    points, spot_id, intensity, size, speed = [], [], [], [], []
    for frame in range(n_frames):
        image = 0.05 * rng.random((height, width))
        bleach = np.exp(-frame / 30)
        for spot in range(n_spots):
            center = np.clip(start[spot] + frame * velocity[spot], 0, (height - 1, width - 1))
            peak = amplitude[spot] * bleach
            image += peak * np.exp(-((rows - center[0]) ** 2 + (cols - center[1]) ** 2) / (2 * sigma[spot] ** 2))
            points.append((frame, *center))
            spot_id.append(spot)
            intensity.append(peak)
            size.append(sigma[spot])
            speed.append(float(np.hypot(*velocity[spot])))
        stack[frame] = image

    features = {"spot": spot_id, "intensity": intensity, "size": size, "speed": speed}
    line = np.array([[height * 0.2, width * 0.1], [height * 0.8, width * 0.9]])
    return [
        (stack, {"name": "Spots", "colormap": "magma"}, "image"),
        (
            np.asarray(points),
            {
                "name": "Spot centers",
                "features": features,
                "size": 6,
                "face_color": "#00000000",
                "border_color": "cyan",
            },
            "points",
        ),
        ([line], {"name": "Profile line", "shape_type": "line", "edge_color": "yellow", "edge_width": 1.5}, "shapes"),
    ]


def make_labeled_blobs() -> list[LayerDataTuple]:
    """Image of round blobs with a Labels layer whose features hold area and mean intensity per label.

    Use it with the features widget: selecting markers in the plot selects the matching label.
    """
    rng = np.random.default_rng(7)
    height, width, n_blobs = 160, 160, 12
    rows, cols = np.mgrid[0:height, 0:width]
    image = 0.1 * rng.random((height, width))
    labels = np.zeros((height, width), dtype=np.int32)
    for label in range(1, n_blobs + 1):
        center = rng.uniform(15, height - 15, size=2)
        radius = rng.uniform(5, 14)
        mask = (rows - center[0]) ** 2 + (cols - center[1]) ** 2 <= radius**2
        labels[mask & (labels == 0)] = label
        image[mask] += rng.uniform(0.3, 1.0)

    index = np.arange(1, n_blobs + 1)
    area = np.array([np.count_nonzero(labels == label) for label in index], dtype=float)
    mean_intensity = np.array([image[labels == label].mean() if area[i] else 0.0 for i, label in enumerate(index)])
    features = {"index": index, "area": area, "mean_intensity": mean_intensity}
    return [
        (image, {"name": "Blobs", "colormap": "gray"}, "image"),
        (labels, {"name": "Blob labels", "features": features, "opacity": 0.5}, "labels"),
    ]
