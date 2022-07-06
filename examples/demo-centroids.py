"""Demo example.

Taken and adapted from:
https://www.python-graph-gallery.com/185-lollipop-plot-with-conditional-color
"""
import napari_plot
import numpy as np

# Data
x = np.linspace(0, 2 * np.pi, 100)
y = np.sin(x) + np.random.uniform(size=len(x)) - 0.2

# Create a color if the y axis value is equal or greater than 0
COLORS = np.where(y >= 0, "orange", "skyblue")

# The vertical plot is made using the vline function
viewer = napari_plot.Viewer()
viewer.add_centroids(np.c_[x, y], color=COLORS)
viewer.add_scatter(np.c_[y, x], face_color=COLORS, scaling=False, size=5)

# Add title and axis names
viewer.text_overlay.visible = True
viewer.text_overlay.text = "Evolution of the value of ..."
viewer.axis.x_label = "Value of the variable"
viewer.axis.y_label = "Group"
napari_plot.run()
