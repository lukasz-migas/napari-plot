"""Display image and 1d plot."""
import napari
import numpy as np
from skimage import data

import napari_plot
from napari_plot._qt.qt_viewer import QtViewer

# create the viewer with an image
viewer = napari.view_image(data.astronaut(), rgb=True)

viewer1d = napari_plot.ViewerModel1D()
widget = QtViewer(viewer1d, parent=viewer.window.qt_viewer.parent())
# viewer1d.add_line(np.c_[np.arange(100), np.arange(100) + 300], name="line")
viewer1d.add_centroids(
    np.c_[np.arange(20), np.random.randint(0, 100, 20), np.random.randint(0, 100, 20)],
    name="centroids (y)",
    orientation="horizontal",
)
viewer1d.add_centroids(
    np.c_[np.arange(20), np.random.randint(0, 100, 20), np.random.randint(0, 100, 20)],
    name="centroids (x)",
    orientation="vertical",
)
viewer1d.add_centroids(np.c_[np.zeros(100), np.arange(100)], name="centroids (y)")
viewer1d.add_scatter(np.c_[np.arange(100), np.arange(100)], name="scatter")
viewer1d.add_region([[0, 50]], face_color="#FF0000", opacity=0.5, name="region")
viewer.window.add_dock_widget(widget, area="bottom", name="Line Widget")

napari.run()
