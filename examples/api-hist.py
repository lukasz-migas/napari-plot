"""Example histogram API."""
import napari_plot
import numpy as np

# Fixing random state for reproducibility
np.random.seed(19680801)

mu, sigma = 100, 15
x = mu + sigma * np.random.randn(10000)

viewer1d = napari_plot.Viewer()
viewer1d.hist(x, 50, density=True, color="green")

napari_plot.run()
