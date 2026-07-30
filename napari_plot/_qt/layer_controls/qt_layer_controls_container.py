"""Layer controls."""

import napari._qt.layer_controls.qt_layer_controls_container
from napari._qt.layer_controls.qt_layer_controls_container import (
    QtLayerControlsContainer as NapariQtLayerControlsContainer,
)
from napari.utils.events import Event

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


class QtLayerControlsContainer(NapariQtLayerControlsContainer):
    """Layer controls container with built-in control styling metadata."""

    def _add(self, event: Event) -> None:
        """Add controls and mark those supplied by napari for scoped QSS rules."""
        super()._add(event)
        controls = self.widgets[event.value]
        controls.setProperty(
            "napari_builtin",
            controls.__class__.__module__.startswith("napari."),
        )


__all__ = [
    "QtCentroidControls",
    "QtInfLineControls",
    "QtLayerControlsContainer",
    "QtLineControls",
    "QtMultiLineControls",
    "QtRegionControls",
    "QtScatterControls",
    "layer_to_controls",
]
