"""Example showing how to use the MultiLine layer type.

The MultiLine layer accepts data of different sizes. You can provide dict of `xs` and `ys` of arbitrary lengths
as long as the number of lines arrays is the same and the corresponding arrays have identical size.
"""

import numpy as np

import napari_plot


def update_fps(fps):
    """Update fps."""
    viewer1d.text_overlay.text = f"{fps:1.1f} FPS"


n_lines = 20
n_pts = np.random.randint(1000, 5000, n_lines)
xs = []
ys = []
for i in range(n_lines):
    xs.append(np.linspace(0, 1000, n_pts[i]))
    ys.append(np.random.uniform(0, 1, size=n_pts[i]) + i)

viewer1d = napari_plot.Viewer()
viewer1d.text_overlay.visible = True
# note: this is using a private attribute, so it might break
# without warning in future versions!
viewer1d.window._qt_viewer.canvas._scene_canvas.measure_fps(callback=update_fps)
viewer1d.add_multi_line({"xs": xs, "ys": ys})

if __name__ == "__main__":
    napari_plot.run()
