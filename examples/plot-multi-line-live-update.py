"""Example showing how to use the MultiLine layer type.

This example shows how one could update the MultiLine layer without changes to e.g. colors. The layer implements
a `stream` method which rapidly replaces existing data with new data and triggers an canvas update.
This method does not do many checks so you must make sure that whatever data you replace, it has the same
characteristics as the original or at least it's valid.
"""
import napari_plot
import numpy as np
from napari.qt import thread_worker
import time


def update_fps(fps):
    """Update fps."""
    viewer1d.text_overlay.text = f"{fps:1.1f} FPS"


def make_data():
    """Return two sets of data"""
    xs, ys = [], []
    for i in range(n_lines):
        xs.append(np.linspace(0, 1000, n_pts[i]))
        ys.append(np.random.uniform(0, 1, size=n_pts[i]) + i)
    return {"xs": xs, "ys": ys}


def update_layer(data):
    """Update layer data."""
    layer.stream(data)


@thread_worker(
    connect={"yielded": update_layer},
)
def run_update(*_):
    """Function that will run for fair amount of time and try to update the canvas every 50ms."""
    for i in range(100_000):
        yield make_data()
        time.sleep(0.01)


n_lines = 50
n_pts = np.full(n_lines, fill_value=2000)
data = make_data()
colors = np.random.random((n_lines, 3))

viewer1d = napari_plot.Viewer()
viewer1d.text_overlay.visible = True
viewer1d.text_overlay.color = "red"
viewer1d.text_overlay.font_size = 25
viewer1d.window.qt_viewer.canvas.measure_fps(callback=update_fps)
layer = viewer1d.add_multi_line(data, color=colors, name="MultiLine")
run_update()
napari_plot.run()
