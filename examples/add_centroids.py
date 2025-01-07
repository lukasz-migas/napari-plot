"""Example showing how to plot centroids."""

import napari_plot
import numpy as np

mu, sigma = 0, 0.1  # mean and standard deviation
s = np.random.normal(mu, sigma, 1000)
counts, bins = np.histogram(s, bins=50)

viewer1d = napari_plot.Viewer()
viewer1d.add_centroids(np.c_[bins[1::], counts], name="Centroids")
viewer1d.add_inf_line([0], orientation="vertical", color="cyan", name="Zero-line")
viewer1d.text_overlay.text = "Distribution"
viewer1d.text_overlay.visible = True

if __name__ == "__main__":
    napari_plot.run()
