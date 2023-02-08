"""Plotting interface."""
import napari_plot
import numpy as np

viewer1d = napari_plot.Viewer()

t = np.linspace(-10, 10, 100)
sig = 1 / (1 + np.exp(-t))

viewer1d.axhline(y=0, color="red", linestyle="--")
viewer1d.axhline(y=0.5, color="red", linestyle=":")
viewer1d.axhline(y=1.0, color="red", linestyle="--")
viewer1d.axvline(color="grey")
# viewer1d.axline((0, 0.5), slope=0.25, color="black", linestyle=(0, (5, 5)))
viewer1d.plot(t, sig, linewidth=2, label=r"$\sigma(t) = \frac{1}{1 + e^{-t}}$")
viewer1d.camera.x_range = (-10, 10)
viewer1d.camera.y_range = (-0.1, 1.1)
viewer1d.axis.x_label = "t"

napari_plot.run()
