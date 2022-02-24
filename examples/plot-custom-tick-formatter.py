"""Custom formatter."""
import napari_plot
import numpy as np


def formatter(val):
    """Custom formatter. It takes in single argument and returns a string."""
    return f"{val:.3f}"


viewer1d = napari_plot.Viewer()

# Formatter can be a standard function or lambda
viewer1d.axis.x_tick_formatter = formatter
viewer1d.axis.y_tick_formatter = lambda val: f">>{val:.1f}<<"


t = np.linspace(0, 2 * np.pi, 400)
r = 0.5 + np.cos(t)
x, y = r * np.cos(t), r * np.sin(t)

viewer1d.add_line(np.c_[x, y], color="orange")
viewer1d.camera.x_range = (-0.25, 1.75)
viewer1d.camera.y_range = (-1, 1)
napari_plot.run()
