"""Multiple infinite regions in a single layer."""
import napari_1d
import numpy as np
from napari_1d._qt.qt_window import make_window

viewer1d, widget, main = make_window()
viewer1d.add_line(np.c_[np.arange(100), np.random.randint(0, 1000, 100)], name="line")

# min_val, max_val = np.iinfo(np.int64).min, np.iinfo(np.int64).max

regions = [
    ([25, 50], "vertical"),
    ([500, 750], "horizontal"),
    ([80, 90], "vertical"),
    # np.array([[min_val, 25], [min_val, 75], [max_val, 75], [max_val, 25]]),
    # np.array([[250, min_val], [250, max_val], [500, max_val], [500, min_val]]),
    # np.array([[750, min_val], [750, max_val], [900, max_val], [900, min_val]]),
]

layer = viewer1d.add_region(
    regions,
    # orientation=["vertical", "horizontal", "horizontal"],
    face_color=["red", "green", "yellow"],
    opacity=0.5,
    name="Infinite Region",
)
napari_1d.run()
