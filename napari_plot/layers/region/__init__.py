"""Init"""
from napari_plot.layers.region import _region_key_bindings
from napari_plot.layers.region.region import Region  # noqa: F401

# Note that importing _region_mouse_bindings is needed as the Region layer gets
# decorated with keybindings during that process, but it is not directly needed
# by our users and so is deleted below
del _region_key_bindings
