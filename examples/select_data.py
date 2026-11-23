"""Drag a box over the plot to collect indices from both selected layers.

Try the Lasso and Polygon tools in the toolbar to select the same data with
different shapes. The label shows the size of the selection on each layer.
"""

import numpy as np
from napari.utils.events import Event

import napari_plot

rng = np.random.default_rng(17)
x = np.linspace(0, 10, 80)
signal = np.sin(x)

viewer = napari_plot.Viewer(title="Selecting observations")
line = viewer.plot(x, signal, name="Model", color="steelblue")
points = viewer.scatter(x, signal + rng.normal(0, 0.2, len(x)), name="Observations", color="orange", scaling=False)
viewer.axis.x_label = "Time (s)"
viewer.axis.y_label = "Signal (a.u.)"
viewer.set_legend_from_layers(position="bottom_right")
summary = viewer.add_text_overlay("Drag a box over the data", position="top_left", box=True)


def report_selection(event: Event) -> None:
    """Show counts and print the selected indices for each layer."""
    summary.text = "  |  ".join(f"{layer.name}: {len(indices)}" for layer, indices in event.value.items())
    for layer, indices in event.value.items():
        print(layer.name, sorted(indices))
    print("Selection vertices (y, x):", viewer.drag_tool.vertices)


viewer.layers.selection.select_only(line)
viewer.layers.selection.add(points)
viewer.events.selection.connect(report_selection)
viewer.drag_tool.active = "box_select"
viewer.margins = (0.03, 0.08)
viewer.reset_view()

if __name__ == "__main__":
    napari_plot.run()
