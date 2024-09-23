"""Example showing simple line and 'infinite' line to show the apex"""

import napari_plot
import numpy as np

viewer1d = napari_plot.Viewer()
x = np.arange(0.0, 10.0, 0.01)
y = np.sin(2 * np.pi * x)
viewer1d.add_line(np.c_[x, y], name="Sin", color="#FF0000")
peaks_x = x[np.where(y == 1.0)]
viewer1d.add_inf_line(peaks_x, orientation="vertical", color="#00FFFF", opacity=0.5, name="Max")
peaks_x = x[np.where(y == -1.0)]
viewer1d.add_inf_line(peaks_x, orientation="vertical", color="#FFFF00", opacity=0.5, name="Min")
viewer1d.axis.x_label = "time (s)"
viewer1d.axis.y_label = "voltage (mV)"

if __name__ == "__main__":
    napari_plot.run()
