"""Scatter API example."""
import napari_plot
import numpy as np

viewer1d = napari_plot.Viewer()

# simple plotting without specifying any parameters
x = np.arange(100)
y = np.sin(x)
viewer1d.scatter(x, y)
# specify size and color of the scatter points
y = np.cos(x)
size = np.linspace(0, 10, 100)
color = np.random.rand(100, 4)
viewer1d.scatter(x, y, s=size, c=color)

napari_plot.run()
