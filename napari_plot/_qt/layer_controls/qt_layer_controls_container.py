"""Layer controls."""

from __future__ import annotations

from typing import TYPE_CHECKING

import napari._qt.layer_controls.qt_layer_controls_container
import qtextra.helpers as hp
from napari._qt.layer_controls.dynamic.qt_dynamic_layer_controls import QtDynamicLayerControls
from napari._qt.layer_controls.dynamic.widgets import QtOpacityBlendingControls
from napari._qt.layer_controls.qt_layer_controls_container import (
    QtLayerControlsContainer as NapariQtLayerControlsContainer,
    create_qt_layer_controls,
)
from napari.settings import get_settings
from napari.utils.events import Event
from qtpy.QtWidgets import QFrame

from napari_plot._qt.layer_controls.qt_bar_controls import QtBarControls
from napari_plot._qt.layer_controls.qt_centroids_controls import QtCentroidControls
from napari_plot._qt.layer_controls.qt_infline_controls import QtInfLineControls
from napari_plot._qt.layer_controls.qt_line_controls import QtLineControls
from napari_plot._qt.layer_controls.qt_multiline_controls import QtMultiLineControls
from napari_plot._qt.layer_controls.qt_region_controls import QtRegionControls
from napari_plot._qt.layer_controls.qt_scatter_controls import QtScatterControls
from napari_plot._qt.layer_controls.qt_text_controls import QtTextControls
from napari_plot.layers import Bar, Centroids, InfLine, Line, MultiLine, Region, Scatter, Text

if TYPE_CHECKING:
    from napari.layers import Layer

    from napari_plot.components.viewer_model import ViewerModel

layer_to_controls = {
    Bar: QtBarControls,
    Line: QtLineControls,
    Centroids: QtCentroidControls,
    Scatter: QtScatterControls,
    Region: QtRegionControls,
    InfLine: QtInfLineControls,
    MultiLine: QtMultiLineControls,
    Text: QtTextControls,
}


# need to overwrite napari' default mapping of layer : control of layers to add our custom layers
napari._qt.layer_controls.qt_layer_controls_container.layer_to_controls.update(layer_to_controls)


class QtSharedLayerControls(QFrame):
    """Edit opacity and blending across custom or mixed layer selections."""

    ndisplay: int = 2

    def __init__(self, layers: list[Layer]) -> None:
        super().__init__()
        self.setObjectName("layer")
        self.controls = QtOpacityBlendingControls(layers, parent=self)
        self._controls = [self.controls]
        layout = hp.make_form_layout(parent=self)
        for widgets in self.controls.get_widget_controls():
            layout.addRow(*widgets)

    def deleteLater(self) -> None:
        """Disconnect layer events before disposing of the selection panel."""
        self.controls.disconnect_widget_controls()
        super().deleteLater()


class QtLayerControlsContainer(NapariQtLayerControlsContainer):
    """Layer controls container with built-in control styling metadata."""

    def __init__(self, viewer: ViewerModel) -> None:
        super().__init__(viewer)
        for layer in viewer.layers:
            self._add(Event("inserted", value=layer))
        self._populate()

    def _add(self, event: Event) -> None:
        """Add controls and mark those supplied by napari for scoped QSS rules."""
        layer = event.value
        controls = create_qt_layer_controls(layer)
        controls.ndisplay = self.viewer.dims.ndisplay
        self.addWidget(controls)
        self.widgets[layer] = controls
        controls.setProperty(
            "napari_builtin",
            controls.__class__.__module__.startswith("napari."),
        )

    def _remove(self, event: Event) -> None:
        controls = self.widgets.pop(event.value)
        self.removeWidget(controls)
        controls.hide()
        controls.deleteLater()

    def _populate(self) -> None:
        if self.panel is not None:
            self.removeWidget(self.panel)
            self.panel.hide()
            self.panel.deleteLater()
            self.panel = None
        layers = [layer for layer in self.viewer.layers if layer in self.viewer.layers.selection]
        if not layers:
            self.setCurrentWidget(self.empty_widget)
            return
        custom = any(isinstance(layer, tuple(layer_to_controls)) for layer in layers)
        if len(layers) == 1 and (custom or not get_settings().experimental.dynamic_layer_controls):
            self.setCurrentWidget(self.widgets[layers[0]])
            return
        self.panel = QtSharedLayerControls(layers) if custom else QtDynamicLayerControls(layers)
        self.panel.ndisplay = self.viewer.dims.ndisplay
        self.addWidget(self.panel)
        self.setCurrentWidget(self.panel)


__all__ = [
    "QtBarControls",
    "QtCentroidControls",
    "QtInfLineControls",
    "QtLayerControlsContainer",
    "QtLineControls",
    "QtMultiLineControls",
    "QtRegionControls",
    "QtScatterControls",
    "QtTextControls",
    "layer_to_controls",
]
