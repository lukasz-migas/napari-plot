"""Layer controls."""

import napari._qt.layer_controls.qt_layer_controls_container

from napari_plot._qt.layer_controls.qt_centroids_controls import QtCentroidControls
from napari_plot._qt.layer_controls.qt_infline_controls import QtInfLineControls
from napari_plot._qt.layer_controls.qt_line_controls import QtLineControls
from napari_plot._qt.layer_controls.qt_multiline_controls import QtMultiLineControls
from napari_plot._qt.layer_controls.qt_region_controls import QtRegionControls
from napari_plot._qt.layer_controls.qt_scatter_controls import QtScatterControls
from napari_plot.layers import Centroids, InfLine, Line, MultiLine, Region, Scatter

layer_to_controls = {
    Line: QtLineControls,
    Centroids: QtCentroidControls,
    Scatter: QtScatterControls,
    Region: QtRegionControls,
    InfLine: QtInfLineControls,
    MultiLine: QtMultiLineControls,
}


# need to overwrite napari' default mapping of layer : control of layers to add our custom layers
napari._qt.layer_controls.qt_layer_controls_container.layer_to_controls.update(layer_to_controls)
