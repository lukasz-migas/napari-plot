"""Multiple infinite lines in a single layer."""
import napari_1d
import numpy as np
from napari_1d._qt.qt_window import make_window

viewer1d, widget, main = make_window()
viewer1d.add_line(np.c_[np.arange(1000), np.random.randint(0, 1000, 1000)], name="line")

# You can add infinite lines providing different orientations and colors
layer = viewer1d.add_inf_line(
    [[50], [15], [250]],
    orientations=["vertical", "vertical", "horizontal"],
    width=3,
    color=["red", "white", "green"],
    name="Infinite Line",
)
napari_1d.run()
