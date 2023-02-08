"""Plotting interface."""
import napari_plot
import numpy as np

viewer1d = napari_plot.Viewer()
# create vertical barchart
x = np.arange(1, 10)
y = np.arange(1, 10)
viewer1d.bar(x, y)

# also add horizontal barchart
x = np.arange(10, 19)
viewer1d.barh(x, y, align="edge")

napari_plot.run()
