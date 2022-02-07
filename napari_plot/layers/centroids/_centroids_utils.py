"""Various utilities."""
import typing as ty

import numpy as np


def parse_centroids_data(data: np.ndarray):
    """Preprocess centroids data. Ensure that user-specified data matches expected dimensions."""
    if data is None:
        return np.empty((0, 3))

    data = np.asarray(data)
    # If data includes upper and lower boundaries, return it
    if data.shape[1] == 3:
        return data
    # If data only contains position and height, insert zeros into the array
    elif data.shape[1] == 2:
        data = np.insert(data, 1, np.zeros(data.shape[0]), axis=1)
        return data
    raise NotImplementedError("Cannot parse input data.")


def get_extents(data: np.ndarray, orientation: str) -> np.ndarray:
    """Get data extents."""
    if orientation == "horizontal":
        y = data[:, 0]
        x = data[:, 1::]
    else:
        x = data[:, 0]
        y = data[:, 1::]
    return np.array([[np.min(y), np.min(x)], [np.max(y), np.max(x)]])


def make_centroids(data: np.ndarray, color: np.ndarray, orientation: str) -> ty.Tuple[np.ndarray, np.ndarray]:
    """Make centroids data in the format [[x, 0], [x, y]]"""
    pos = np.zeros((len(data) * 2, 2), dtype=data.dtype)
    colors = np.repeat(color, 2, axis=0)
    # in horizontal centroids, the three columns correspond to x-min, x-max, y
    if orientation == "horizontal":
        pos[:, 1] = np.repeat(data[:, 0], 2)
        pos[1::2, 0] = data[:, 1]
        pos[0::2, 0] = data[:, 2]
    # in vertical centroids, the three columns correspond to x, y-min, y-max
    else:
        pos[:, 0] = np.repeat(data[:, 0], 2)
        pos[1::2, 1] = data[:, 1]
        pos[0::2, 1] = data[:, 2]
    return pos, colors


def make_centroids_color(color):
    """Make array of colors."""
    return np.repeat(color, 2, axis=0)
