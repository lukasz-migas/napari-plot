"""Demo example of InfLine and Region/Span layer-types."""
import numpy as np
from scipy.stats import gaussian_kde, norm, expon

import napari_plot


x = norm.rvs(size=10_000, random_state=2)
y = np.abs(x) * expon.rvs(scale=0.5, size=10_000, random_state=2)

kernel = gaussian_kde(np.vstack([x, y]))
c = kernel(np.vstack([x, y]))

viewer = napari_plot.Viewer()
# add Volcano plot
viewer.scatter(x, y, s=3, edge_color="green", face_color="green", name="Volcano")
# make significant points bigger
sig = (x > 1.8) & (y > 4.5)
viewer.scatter(x[sig], y[sig], s=5, edge_color="red", face_color="red", name="Significant")
# add infinite lines
viewer.add_inf_line([(0, "vertical"), (2.2, "horizontal")], color=["white", "red"], opacity=0.5, name="Infinite lines")

# specify data ranges - infinite lines/regions do not automatically set ranges as they span the entire axes/canvas
viewer.camera.x_range = (-4, 4)
viewer.camera.y_range = (0, 8)
napari_plot.run()
