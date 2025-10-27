"""Example shows a sin and cos scatter points moving over time."""

import time

import numpy as np
from napari.qt import thread_worker

import napari_plot


def update_layer(res):
    """Update layer data."""
    y1, y2 = res
    layer_sin.y = y1
    layer_cos.y = y2


@thread_worker(connect={"yielded": update_layer})
def run_update(*_):
    """Function that will run for fair amount of time and try to update the canvas every 10ms."""
    for i in range(100_000):
        yield np.sin(2 * np.pi * (x - 0.01 * i)), np.cos(2 * np.pi * (x - 0.01 * i))
        time.sleep(0.05)


viewer1d = napari_plot.Viewer()
x = np.arange(0.0, 10.0, 0.01)
window = 0.2
layer_sin = viewer1d.add_scatter(
    np.c_[np.sin(2 * np.pi * x), x], name="Sin", face_color="magenta"
)
layer_cos = viewer1d.add_scatter(
    np.c_[np.cos(2 * np.pi * x), x], name="Cos", face_color="springgreen"
)
run_update()
if __name__ == "__main__":
    napari_plot.run()
