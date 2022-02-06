"""Example showing how to plot multiple line sand adjust axis labels."""
import napari_plot
import numpy as np

viewer1d = napari_plot.Viewer()
x = np.arange(0.0, 10.0, 0.01)
y = np.sin(2 * np.pi * x)
peaks_x = x[np.where(y > 0.95)]
viewer1d.add_line(np.c_[x, y], name="Sin", color="#FF0000")
viewer1d.add_inf_line(peaks_x, orientation="vertical", color="#00FFFF")
viewer1d.axis.x_label = "time (s)"
viewer1d.axis.y_label = "voltage (mV)"
napari_plot.run()
