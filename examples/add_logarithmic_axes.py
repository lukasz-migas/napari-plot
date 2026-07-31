"""Plot positive data using true logarithmic x and y axes."""

import numpy as np

import napari_plot

viewer1d = napari_plot.Viewer()
viewer1d.camera.extent_mode = "restricted"

x = np.logspace(-2, 3, 600)
viewer1d.add_line(np.c_[x, x], name="y = x", color="cyan")
viewer1d.add_line(np.c_[x, np.sqrt(x)], name="y = sqrt(x)", color="orange")

# Scales are independent. Set only x_scale for a semilog-x plot.
viewer1d.axis.x_scale = "log"
viewer1d.axis.y_scale = "log"
viewer1d.axis.x_label = "x (log scale)"
viewer1d.axis.y_label = "y (log scale)"

if __name__ == "__main__":
    napari_plot.run()
