"""Test regions."""
import napari_1d
import numpy as np
from napari_1d._qt.qt_window import make_window

viewer1d, widget, main = make_window()
viewer1d.add_line(np.c_[np.arange(100), np.random.randint(0, 1000, 100)], name="line")

# You can add infinite lines providing different orientations and colors
layer = viewer1d.add_inf_line(
    [50, 15, 250],
    ["vertical", "vertical", "horizontal"],
    width=3,
    color=["red", "white", "green"],
    name="Infinite Line",
)
napari_1d.run()