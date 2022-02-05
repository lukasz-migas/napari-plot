"""Utilities for tests."""
import os
import sys

import numpy as np
import pytest
from napari.utils.misc import camel_to_snake

from napari_plot import Viewer
from napari_plot.layers import Centroids, InfLine, Line, MultiLine, Points, Region, Scatter, Shapes

# data to be used by pytest during various tests
layer_test_data = [
    (Line, np.random.random((10, 2))),
    (Scatter, np.random.random((10, 2))),
    (Points, 20 * np.random.random((10, 2))),
    (Centroids, np.random.random((10, 2))),
    (Centroids, np.random.random((10, 3))),
    (Shapes, 20 * np.random.random((10, 4, 2))),
    (MultiLine, {"xs": [np.random.random(10)], "ys": [np.random.random(10)] * 3}),
    (MultiLine, {"xs": [np.random.random(10)] * 3, "ys": [np.random.random(10)] * 3}),
    (MultiLine, {"x": np.random.random(10), "ys": [np.random.random(10)] * 3}),
    (MultiLine, {"xs": [np.random.random(10)], "ys": [np.random.random(10)]}),
    (MultiLine, {"x": np.random.random(10), "ys": [np.random.random(10)]}),
    (MultiLine, (np.random.random(10), np.random.random(10))),
    (MultiLine, ([np.random.random(10)], [np.random.random(10)])),
    (InfLine, [(25, "vertical"), (50, "vertical")]),
    (InfLine, [25, 50]),
    (Region, [[25, 50], [80, 90]]),
    (Region, [([25, 50], "vertical")]),
]


classes = [Centroids, Line, InfLine, MultiLine, Scatter, Shapes, Points, Region]
names = [cls.__name__ for cls in classes]
layer2addmethod = {cls: getattr(Viewer, "add_" + camel_to_snake(name)) for cls, name in zip(classes, names)}


def add_layer_by_type(viewer, layer_type, data, visible=True):
    """
    Convenience method that maps a LayerType to its add_layer method.

    Parameters
    ----------
    layer_type : LayerTypes
        Layer type to add
    data
        The layer data to view
    """
    return layer2addmethod[layer_type](viewer, data, visible=visible)


skip_on_win_ci = pytest.mark.skipif(
    sys.platform.startswith("win") and os.getenv("CI", "0") != "0",
    reason="Screenshot tests are not supported on windows CI.",
)
