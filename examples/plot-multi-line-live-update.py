"""Example showing how to use the MultiLine layer type.

The MultiLine layer accepts data of different sizes. You can provide dict of `xs` and `ys` of arbitrary lengths
as long as the number of lines arrays is the same and the corresponding arrays have identical size.
"""
import napari_1d
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
    layer.data = data


@thread_worker(
    connect={"yielded": update_layer},
)
def run_update(*_):
    """Function that will run for fair amount of time and try to update the canvas every 50ms."""
    for i in range(100_000):
        yield make_data()
        time.sleep(0.05)


n_lines = 50
n_pts = np.full(n_lines, fill_value=2000)
data = make_data()

viewer1d = napari_1d.Viewer()
viewer1d.text_overlay.visible = True
viewer1d.window.qt_viewer.canvas.measure_fps(callback=update_fps)
layer = viewer1d.add_multi_line(data)
run_update()
napari_1d.run()
