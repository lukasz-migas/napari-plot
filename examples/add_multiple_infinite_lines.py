"""Multiple infinite lines in a single layer."""
import napari_plot
import numpy as np

viewer1d = napari_plot.Viewer()
viewer1d.add_line(np.c_[np.arange(1000), np.random.randint(0, 1000, 1000)], name="line")

# You can add infinite lines providing different orientations and colors
layer = viewer1d.add_inf_line(
    [50, 140, 250],
    orientation=["vertical", "vertical", "horizontal"],
    width=3,
    color=["red", "yellow", "green"],
    name="Infinite Line",
)
if __name__ == "__main__":
    napari_plot.run()
