"""Example showing how to use the MultiLine layer type.

The MultiLine layer is implemented to enable better performance when plotting multiple lines of long length.
In the example below we are plotting several long lines with no noticeable performance drop.
"""
import napari_plot
import numpy as np


def select_data(event):
    """Select data"""
    mask = layer._get_mask_from_path(event.value)
    indices = np.nonzero(mask)[0]
    data = xy[indices, :]
    sel_layer.data = data
    print(f"Selected {len(data)} points.")


n = 150_000
xy = np.random.random((n, 2))
viewer1d = napari_plot.Viewer()
viewer1d.drag_tool.active = "lasso"
viewer1d.drag_tool.events.vertices.connect(select_data)
layer = viewer1d.add_scatter(xy, face_color=np.random.random((n, 4)), scaling=False, name="Your data")
sel_layer = viewer1d.add_scatter(
    None, scaling=False, face_color="yellow", edge_color="green", size=10, name="Selected points"
)
napari_plot.run()
