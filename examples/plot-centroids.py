"""Example showing how to plot centroids."""
import napari_plot
import numpy as np

mu, sigma = 0, 0.1  # mean and standard deviation
s = np.random.normal(mu, sigma, 1000)
counts, bins = np.histogram(s, bins=50)

viewer1d = napari_plot.Viewer()
viewer1d.add_centroids(np.c_[bins[1::], counts])
napari_plot.run()
