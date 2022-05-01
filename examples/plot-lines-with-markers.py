"""Example demonstrating how to easily plot lines and markers."""
import napari_plot
from itertools import cycle
import numpy as np

viewer1d = napari_plot.Viewer()

colors = cycle(["#ff9aa2", "#ffb7b2", "#ffdac1", "#b5ead7", "#c7ceea"])

n_colors = 6
x = np.linspace(0, n_colors)
shift = np.linspace(0, n_colors, n_colors, endpoint=False)
for i, s in enumerate(shift):
    color = next(colors)
    viewer1d.add_line(np.c_[x, np.sin(x + s)], color=color, name=f"Line ({i+1})")
    viewer1d.add_scatter(
        np.c_[x, np.sin(x + s)], face_color=color, edge_color=color, edge_width=0, size=10, name=f"Scatter ({i+1})"
    )
napari_plot.run()
