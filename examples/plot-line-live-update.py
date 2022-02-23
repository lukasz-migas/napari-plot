"""Example shows a sine wave `moving` over time.."""
import time
import napari_plot
import numpy as np
from napari.qt import thread_worker


def update_layer(res):
    """Update layer data."""
    y1, y2 = res
    layer_sin.data = np.c_[x, y1]
    layer_cos.data = np.c_[x, y2]


@thread_worker(connect={"yielded": update_layer})
def run_update(*_):
    """Function that will run for fair amount of time and try to update the canvas every 10ms."""
    for i in range(100_000):
        yield np.sin(2 * np.pi * (x - 0.01 * i)), np.cos(2 * np.pi * (x - 0.01 * i))
        time.sleep(0.01)


viewer1d = napari_plot.Viewer()
x = np.arange(0.0, 10.0, 0.01)
window = 0.2
layer_sin = viewer1d.add_line(np.c_[x, np.sin(2 * np.pi * x)], name="Sin", color="magenta")
layer_cos = viewer1d.add_line(np.c_[x, np.cos(2 * np.pi * x)], name="Cos", color="springgreen")
run_update()
napari_plot.run()
