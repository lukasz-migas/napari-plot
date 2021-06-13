"""Layer controls."""
import napari._qt.layer_controls.qt_layer_controls_container
from napari._qt.layer_controls.qt_layer_controls_container import QtLayerControlsContainer  # noqa

from napari_1d._qt.layer_controls.qt_infline_controls import QtInfLineControls
from napari_1d._qt.layer_controls.qt_line_controls import QtLineControls
from napari_1d._qt.layer_controls.qt_region_controls import QtRegionControls
from napari_1d._qt.layer_controls.qt_scatter_controls import QtScatterControls
from napari_1d.layers import Centroids, InfLine, Line, Region, Scatter

layer_to_controls = {
    Line: QtLineControls,
    Centroids: QtLineControls,
    Scatter: QtScatterControls,
    Region: QtRegionControls,
    InfLine: QtInfLineControls,
}


# need to overwrite napari' default mapping of layer : control of layers to add our custom layers
napari._qt.layer_controls.qt_layer_controls_container.layer_to_controls.update(layer_to_controls)
