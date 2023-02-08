import napari_plot
import numpy as np

# create data to plot
y1 = (90, 55, 40, 65)
y2 = (85, 62, 54, 20)

viewer1d = napari_plot.Viewer()

# create plot
index = np.arange(4)
bar_width = 0.35
opacity = 0.8

rects1 = viewer1d.bar(index, y1, bar_width, opacity=opacity, face_color="blue")
rects2 = viewer1d.bar(index + bar_width, y2, bar_width, opacity=opacity, face_color="green")

viewer1d.axis.x_label = "X-label"
viewer1d.axis.y_label = "Y-label"

napari_plot.run()
