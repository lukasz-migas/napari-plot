"""Example barchart API."""
import napari_plot
import numpy as np

viewer1d = napari_plot.Viewer()

# simple plotting without specifying x-axis
y = np.sin(np.arange(100))
viewer1d.plot(y)
# simple plotting while also specifying x-axis
x = np.arange(50, 100)
y = np.cos(x)
viewer1d.plot(x, y)
# plotting while also specifying as scatter
viewer1d.plot(x, y, fmt="ro")

napari_plot.run()
