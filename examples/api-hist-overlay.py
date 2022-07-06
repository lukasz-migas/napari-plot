"""Example histogram API."""
import napari_plot
import numpy as np

x1 = np.random.normal(0, 0.8, 1000)
x2 = np.random.normal(-2, 1, 1000)
x3 = np.random.normal(3, 2, 1000)

viewer1d = napari_plot.Viewer()
viewer1d.hist(x1, alpha=0.3, density=True, bins=40)
viewer1d.hist(x2, alpha=0.3, density=True, bins=40)
viewer1d.hist(x3, alpha=0.3, density=True, bins=40)

napari_plot.run()
