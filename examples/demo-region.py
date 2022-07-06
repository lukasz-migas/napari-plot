"""Demo example of InfLine and Region/Span layer-types."""
import numpy as np
import napari_plot

start = np.arange(0, 360, 20)
end = start + 10
data = [(s, e) for (s, e) in zip(start, end)]

viewer = napari_plot.Viewer()
# add checkerboard pattern
viewer.add_region(data, orientation="vertical", opacity=0.5, name="Vertical")
viewer.add_region(data, orientation="horizontal", opacity=0.5, name="Horizontal")

# specify data ranges - infinite lines/regions do not automatically set ranges as they span the entire axes/canvas
viewer.camera.x_range = (0, 300)
viewer.camera.y_range = (0, 300)
napari_plot.run()
