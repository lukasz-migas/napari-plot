"""Display image and 1d plot."""
from imimsui.gui_elements.helpers import make_btn

import napari
import numpy as np
from skimage import data

import napari_1d
from napari_1d._qt.qt_viewer import QtViewer

N_POINTS = 1000

def add_line():
    """Line plot"""
    x = np.arange(N_POINTS)
    y = np.random.randint(0, 5000, N_POINTS)
    viewer1d.add_line(np.c_[x, y])


def add_centroids():
    """Centroids plot"""
    x = np.arange(N_POINTS)
    y = np.random.randint(0, 5000, N_POINTS)
    viewer1d.add_centroids(x, y, color=(1., 0., 1., 1.))


def add_scatter():
    """Centroids plot"""
    x = np.random.randint(0, N_POINTS, N_POINTS)
    y = np.random.randint(0, 5000, N_POINTS)
    viewer1d.add_scatter(np.c_[x, y], size=15)


def add_region(orientation):
    """Region plot"""
    xmin, xmax = np.random.randint(0, N_POINTS, 2)
    viewer1d.add_region((xmin, xmax), opacity=0.5, color=(1., 0., 0., 1), orientation=orientation,
                        name="region " + orientation)


def add_infline():
    """Infline plot"""
    pos = np.random.randint(0, N_POINTS, 1)
    viewer1d.add_inf_line(pos)


# create the viewer with an image
viewer = napari.view_image(data.astronaut(), rgb=True)

viewer1d = napari_1d.ViewerModel1D()
widget = QtViewer(viewer1d, parent=viewer.window.qt_viewer.parent())
viewer.window.add_dock_widget(widget, area="bottom", name="Line Widget")

napari.run()
