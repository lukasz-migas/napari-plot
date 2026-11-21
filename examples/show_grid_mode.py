"""Show each line in its own plot cell, with synchronized x/y ranges."""

import numpy as np

import napari_plot

viewer1d = napari_plot.Viewer()
x = np.linspace(0, 10, 200)
for i, color in enumerate(["red", "orange", "cyan", "lime"]):
    viewer1d.add_line(np.c_[x, np.sin(x + i)], name=f"signal {i}", color=color)
viewer1d.grid_lines.visible = True
viewer1d.legend.visible = True
# overlays with `gridded=True` are drawn in every cell; others stay in the first cell
note = viewer1d.add_text_overlay("sin(x + i)", position="bottom_right")
note.gridded = True
# one cell per layer; `stride` groups several layers into one cell and `spacing` separates the cells
viewer1d.canvas.grid.enabled = True
viewer1d.canvas.grid.spacing = 10

if __name__ == "__main__":
    napari_plot.run()
