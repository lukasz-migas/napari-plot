"""Layer controls."""
import napari._qt.layer_controls.qt_layer_controls_container

from napari._qt.layer_controls.qt_image_controls import QtImageControls
from napari._qt.layer_controls.qt_labels_controls import QtLabelsControls
from napari._qt.layer_controls.qt_points_controls import QtPointsControls
from napari._qt.layer_controls.qt_shapes_controls import QtShapesControls
from napari.layers import Image, Labels, Points, Shapes
from napari_1d._qt.layer_controls.qt_infline_controls import QtInfLineControls
from napari_1d._qt.layer_controls.qt_line_controls import QtLineControls
from napari_1d._qt.layer_controls.qt_region_controls import QtRegionControls
from napari_1d._qt.layer_controls.qt_scatter_controls import QtScatterControls
from napari_1d.layers import Centroids, InfLine, Line, Region, Scatter

layer_to_controls = {
    Labels: QtLabelsControls,
    Image: QtImageControls,  # must be after Labels layer
    Shapes: QtShapesControls,
    Points: QtPointsControls,
    Line: QtLineControls,
    Centroids: QtLineControls,
    Scatter: QtScatterControls,
    Region: QtRegionControls,
    InfLine: QtInfLineControls,
}

napari._qt.layer_controls.qt_layer_controls_container.layer_to_controls = (
    layer_to_controls
)
from napari._qt.layer_controls import QtLayerControlsContainer  # noqa
