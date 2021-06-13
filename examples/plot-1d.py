"""Display image and 1d plot."""
from skimage import data
import numpy as np

import napari
import napari_1d
from napari_1d._qt.qt_viewer import QtViewer

# create the viewer with an image
viewer = napari.view_image(data.astronaut(), rgb=True)

viewer1d = napari_1d.ViewerModel1D()
viewer1d.add_centroids(np.c_[np.arange(100), np.arange(100)])
viewer1d.add_scatter(np.c_[np.arange(100), np.arange(100)])


widget = QtViewer(viewer1d)
viewer.window.add_dock_widget(widget, area="bottom", name="Line Widget")

napari.run()
