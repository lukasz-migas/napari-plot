"""
Add text annotations
====================

Display labels at xy plot coordinates with scalar and per-label styling.

.. tags:: visualization-basic
"""

import numpy as np

import napari_plot

viewer1d = napari_plot.Viewer()
x = np.linspace(0, 2, 200)
y = np.sin(2 * np.pi * x)
viewer1d.add_line(np.c_[x, y], color="gray")

viewer1d.add_text(
    [[0.25, 1], [0.75, -1], [1.25, 1], [1.75, -1]],
    ["peak", "trough", "peak", "trough"],
    size=[12, 16, 20, 24],
    color=["cyan", "orange", "magenta", "yellow"],
    alignment=["left", "center", "right", "center"],
    vertical_alignment=["bottom", "top", "bottom", "top"],
    rotation=[0, -10, 10, 0],
    offset=(0, 0.05),
    scaling=True,
    name="Annotations",
)

if __name__ == "__main__":
    napari_plot.run()
