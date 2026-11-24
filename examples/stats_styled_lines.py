"""Styled distributions
==================

Compare average response curves, a step histogram, and a normalized KDE.

.. tags:: statistical-plots
"""

import numpy as np
import pandas as pd

import napari_plot

rng = np.random.default_rng(29)
time = np.tile(np.arange(7), 24)
method = np.repeat(["Fast", "Slow"], 84)
response = 3 + (time / 6) ** np.repeat([0.7, 2.0], 84) + rng.normal(0, 0.18, len(time))
data = pd.DataFrame({"time": time, "response": response, "method": method})
palette = {"Fast": "steelblue", "Slow": "orange"}

viewer = napari_plot.Viewer(title="Comparing two response curves")
viewer.window.resize(1080, 720)
viewer.margins = (0.05, 0.06)
grid = viewer.canvas.grid
grid.shape = (2, 2)
grid.sharex = grid.sharey = False
grid.group_by_metadata = True
grid.spacing = 10

viewer.lineplot(
    data,
    x="time",
    y="response",
    hue="method",
    size="method",
    style="method",
    palette=palette,
    dashes={"Fast": (), "Slow": (5, 3)},
    markers={"Fast": "disc", "Slow": "square"},
    sizes=(2, 4),
    errorbar="se",
    legend=False,
    group="curves",
)
viewer.histplot(
    data,
    x="response",
    hue="method",
    palette=palette,
    element="step",
    fill=False,
    bins=12,
    legend=False,
    group="histogram",
)
viewer.kdeplot(data, x="response", hue="method", palette=palette, multiple="fill", fill=True, legend=False, group="kde")
viewer.ecdfplot(data, x="response", hue="method", palette=palette, legend=False, group="ecdf")

panels = (
    ("curves", "Time (s)", "Mean response"),
    ("histogram", "Response", "Count"),
    ("kde", "Response", "Density fraction"),
    ("ecdf", "Response", "Cumulative proportion"),
)
for index, (group, x_label, y_label) in enumerate(panels):
    cell = grid.cell(*divmod(index, 2))
    cell.group = group
    cell.x_label = x_label
    cell.y_label = y_label

grid.enabled = True
viewer.set_legend(
    [{"label": method, "marker": "square", "color": color} for method, color in palette.items()],
    title="Method",
    ncols=2,
    position="top_left",
)
viewer.legend.gridded = False
viewer.reset_view()

if __name__ == "__main__":
    napari_plot.run()
