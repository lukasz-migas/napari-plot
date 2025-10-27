"""Init"""

from napari_plot.layers.centroids import _centroids_key_bindings
from napari_plot.layers.centroids.centroids import Centroids  # noqa: F401

# Note that importing _points_key_bindings is needed as the Points layer gets
# decorated with keybindings during that process, but it is not directly needed
# by our users and so is deleted below
del _centroids_key_bindings
