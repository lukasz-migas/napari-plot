"""Summary plots
=================

Compare stacked sensor output, an uneven-bin histogram, and horizontal bars.

.. tags:: plotting
"""

import numpy as np

import napari_plot

viewer = napari_plot.Viewer(title="Summarizing sensor output")
viewer.window.resize(1160, 640)
viewer.axis.y_max_size = 88
viewer.axis.y_label_margin = 57
viewer.margins = (0.05, 0.08)
grid = viewer.canvas.grid
grid.shape = (1, 3)
grid.sharex = grid.sharey = False
grid.spacing = 12
grid.group_by_metadata = True

stack = grid.cell(0, 0)
stack.group = "stack"
stack.x_label = "Time (s)"
stack.y_label = "Combined output"
time = np.linspace(0, 10, 100)
viewer.stackplot(
    time,
    1 + 0.4 * np.sin(time),
    1.1 + 0.3 * np.cos(time),
    fill_color=["steelblue", "orange"],
    border_width=0,
    metadata={"napari_plot.group": "stack"},
    name="Two sensors",
)

histogram = grid.cell(0, 1)
histogram.group = "histogram"
histogram.x_label = "Output"
histogram.y_label = "Samples per bin"
rng = np.random.default_rng(8)
viewer.hist(
    rng.gamma(3, 0.7, 200),
    bins=[0, 1, 1.5, 2, 3, 5, 8],
    color="steelblue",
    metadata={"napari_plot.group": "histogram"},
    name="Uneven bins",
)

bars = grid.cell(0, 2)
bars.group = "bars"
bars.x_label = "Output"
bars.y_label = "Sensor"
bars.y_categories = ("A", "B", "C")
viewer.hbar(
    [0, 1, 2],
    [2.1, 3.2, 2.7],
    width=0.5,  # Thickness, since the endpoints are the second positional argument.
    baseline=1.0,
    color="orange",
    metadata={"napari_plot.group": "bars"},
    name="Output above baseline",
)

grid.enabled = True
viewer.reset_view()

if __name__ == "__main__":
    napari_plot.run()
