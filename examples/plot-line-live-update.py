"""Example shows a sine wave `moving` over time.."""
import time
import napari_plot
import numpy as np
from napari.qt import thread_worker


def update_layer(y):
    """Update layer data."""
    layer.data = np.c_[x, y]


@thread_worker(connect={"yielded": update_layer})
def run_update(*_):
    """Function that will run for fair amount of time and try to update the canvas every 10ms."""
    for i in range(100_000):
        yield np.sin(2 * np.pi * (x - 0.01 * i))
        time.sleep(0.01)


viewer1d = napari_plot.Viewer()
x = np.arange(0.0, 10.0, 0.01)
y = np.sin(2 * np.pi * x)
pos_x = x[np.where(y == 1.0)]
window = 0.2
layer = viewer1d.add_line(np.c_[x, y], name="Sin", color="#FF0000")
run_update()
napari_plot.run()
