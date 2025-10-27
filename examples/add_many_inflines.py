"""Example showing how to plot multiple line sand adjust axis labels."""

import numpy as np
from koyo.color import get_random_hex_color

import napari_plot

viewer1d = napari_plot.Viewer()
x = np.arange(0.0, 10.0, 0.01)
y = np.sin(2 * np.pi * x)
viewer1d.add_line(np.c_[x, y], name="Sin", color="#FF0000")

horizontal_lines = np.linspace(-1, 1, 100)
viewer1d.add_inf_line(
    horizontal_lines,
    orientation="horizontal",
    color=[get_random_hex_color() for _ in range(100)],
)

vertical_lines = np.linspace(0, 10, 100)
viewer1d.add_inf_line(vertical_lines, orientation="vertical")

viewer1d.axis.x_label = "time (s)"
viewer1d.axis.y_label = "voltage (mV)"

if __name__ == "__main__":
    napari_plot.run()
