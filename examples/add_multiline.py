"""Example showing how to use the MultiLine layer type.

The MultiLine layer is implemented to enable better performance when plotting multiple lines of long length.
In the example below we are plotting several long lines with no noticeable performance drop.
"""

import numpy as np

import napari_plot


def update_fps(fps):
    """Update fps."""
    viewer1d.text_overlay.text = f"{fps:1.1f} FPS"


n_pts = 250
n_lines = 3
xs = [np.linspace(0, 1000, n_pts)]
ys = []
for i in range(n_lines):
    ys.append(np.random.uniform(0, 1, size=n_pts) + i)

viewer1d = napari_plot.Viewer()
viewer1d.text_overlay.visible = True
# note: this is using a private attribute, so it might break
# without warning in future versions!
viewer1d.window._qt_viewer.canvas._scene_canvas.measure_fps(callback=update_fps)
viewer1d.add_multi_line({"xs": xs, "ys": ys})

if __name__ == "__main__":
    napari_plot.run()
