"""Compare two phase-shifted signals on a labeled 1D plot."""

import numpy as np

import napari_plot

viewer1d = napari_plot.Viewer()
viewer1d.camera.extent_mode = "restricted"
x = np.linspace(0, 2, 401)
viewer1d.plot(x, np.sin(2 * np.pi * x), name="Sine", color="royalblue")
viewer1d.plot(x, np.sin(2 * np.pi * x + np.pi / 2), name="Cosine", color="darkorange")
viewer1d.axis.x_label = "Time (s)"
viewer1d.axis.y_label = "Amplitude (a.u.)"
viewer1d.legend.visible = True
if __name__ == "__main__":
    napari_plot.run()
