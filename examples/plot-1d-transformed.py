"""Display image and 1d plot."""
import napari
import numpy as np
from skimage import data

import napari_1d
from napari_1d._qt.qt_viewer import QtViewer

# create the viewer with an image
viewer = napari.view_image(data.astronaut(), rgb=True)

viewer1d = napari_1d.ViewerModel1D()
widget = QtViewer(viewer1d, parent=viewer.window.qt_viewer.parent())
viewer1d.add_line(np.c_[np.arange(100), np.arange(100)], name="line")
viewer.window.add_dock_widget(widget, area="bottom", name="Line Widget")
napari.run()
