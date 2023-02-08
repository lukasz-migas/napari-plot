"""Example showing how to use the MultiLine layer type.

The MultiLine layer is implemented to enable better performance when plotting multiple lines of long length.
In the example below we are plotting several long lines with no noticeable performance drop.
"""
import napari_plot
import numpy as np


def select_data(event):
    """Select data"""
    indices = layer._get_mask_from_path(event.value, as_indices=True)
    data = yx[indices, :]
    sel_layer.data = data
    print(f"Selected {len(data)} points.")


n = 150000
yx = np.random.random((n, 2))
viewer1d = napari_plot.Viewer()
viewer1d.drag_tool.active = "lasso"
viewer1d.drag_tool.events.vertices.connect(select_data)
layer = viewer1d.add_scatter(yx, face_color=np.random.random((n, 4)), scaling=False, name="Your data")
sel_layer = viewer1d.add_scatter(
    None, scaling=False, face_color="yellow", edge_color="green", size=10, name="Selected points"
)
if __name__ == "__main__":
    napari_plot.run()
