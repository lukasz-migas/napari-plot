"""This example illustrates how you can `crop` certain regions of your line plot by simply using NaNs"""
import napari_plot
import numpy as np


viewer1d = napari_plot.Viewer()
n_pts = 500
x = np.linspace(0, 1000, n_pts)

y = np.random.uniform(0, 1, size=n_pts) + 100
for i in range(0, 500, 50):
    y[i : i + 25] = np.nan
viewer1d.add_line(np.c_[x, y], name="Line")
napari_plot.run()
