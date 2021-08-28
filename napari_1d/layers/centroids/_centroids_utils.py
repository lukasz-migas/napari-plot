"""Various utilities."""
import numpy as np


def preprocess_centroids(data: np.ndarray):
    """Preprocess centroids data. Ensure that user-specified data matches expected dimensions."""
    data = np.asarray(data)

    # check if data includes the upper and lower boundaries - if so, move on
    if data.shape[1] == 3:
        return data
    if data.shape[1] == 2:
        lower = np.zeros(data.shape[0])
        data = np.insert(data, lower, axis=1)
        return data
