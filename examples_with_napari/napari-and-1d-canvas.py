"""Display image and 1d plot."""
import napari
import numpy as np
from skimage import data

import napari_plot
from napari_plot._qt.qt_viewer import QtViewer

# create the viewer with an image
viewer = napari.view_image(data.astronaut(), rgb=True)


viewer1d = napari_plot.ViewerModel1D()
widget = QtViewer(viewer1d)
viewer.window.add_dock_widget(widget, area="bottom", name="Line Widget")

# example data
x = np.arange(0.1, 4, 0.1)
y1 = np.exp(-1.0 * x)
y2 = np.exp(-0.5 * x)

# example variable error bar values
y1err = 0.1 + 0.1 * np.sqrt(x)
y2err = 0.1 + 0.1 * np.sqrt(x / 2)


viewer1d.add_line(np.c_[x, y1], name="Line 1", color="lightblue")
viewer1d.add_centroids(
    np.c_[x, y1 - y1err, y1 + y1err], orientation="vertical", color="lightblue", opacity=0.5, name="Line 1 (errors)"
)
viewer1d.add_line(np.c_[x, y2], name="Line 2", color="orange")
viewer1d.add_centroids(
    np.c_[x, y2 - y2err, y2 + y2err], orientation="vertical", color="orange", opacity=0.5, name="Line 2 (errors)"
)
viewer1d.camera.extent = (-0.1, 4.1, 1.0, -0.3)
viewer1d.axis.x_label = ""
viewer1d.axis.y_label = ""
viewer1d.reset_view()
if __name__ == "__main__":
    napari.run()
