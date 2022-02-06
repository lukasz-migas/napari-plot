"""Example showing how to use the MultiLine layer type.

The MultiLine layer is implemented to enable better performance when plotting multiple lines of long length.
In the example below we are plotting several long lines with no noticeable performance drop.
"""
import napari_plot
import numpy as np

xy = np.random.random((500, 2))

viewer1d = napari_plot.Viewer()
viewer1d.add_scatter(xy, scaling=False)
napari_plot.run()
