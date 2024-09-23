"""Infinite line"""

from napari_plot.layers.infline import _infline_key_bindings
from napari_plot.layers.infline.infline import InfLine  # noqa: F401

# Note that importing _infline_key_bindings is needed as the InfLine layer gets
# decorated with keybindings during that process, but it is not directly needed
# by our users and so is deleted below
del _infline_key_bindings
