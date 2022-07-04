"""Example histogram API."""
import napari_plot
import numpy as np

x = np.random.normal(size=50000)
y = x * 3 + np.random.normal(size=50000)

viewer1d = napari_plot.Viewer()
viewer1d.hist2d(x, y, bins=(50, 50), cmap="viridis")
viewer1d.hist2d(x, y, bins=(300, 300), cmap="viridis")
viewer1d.hist2d(x, y, bins=(1000, 1000), cmap="viridis")
napari_plot.run()
