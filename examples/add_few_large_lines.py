"""Example showing how to plot multiple line sand adjust axis labels."""

import numpy as np

import napari_plot


def update_fps(fps):
    """Update fps."""
    viewer1d.text_overlay.text = f"{fps:1.1f} FPS"


n_pts = 250_000
n_lines = 5
x = np.linspace(0, 1000, n_pts)
ys = []
viewer1d = napari_plot.Viewer()
viewer1d.text_overlay.visible = True
# note: this is using a private attribute, so it might break
# without warning in future versions!
viewer1d.window._qt_viewer.canvas._scene_canvas.measure_fps(callback=update_fps)

for i in range(n_lines):
    y = np.random.uniform(0, 1, size=n_pts) + i
    viewer1d.add_line(np.c_[x, y], name=f"Line {i}")

if __name__ == "__main__":
    napari_plot.run()
