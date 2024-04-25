"""Scatter widget.

This widget is inspired by ScatterWidget in https://github.com/dstansby/napari-matplotlib
"""
import typing as ty
from contextlib import suppress
from warnings import warn

import napari
import numpy as np
from napari.layers import Image

from napari_plot._plot_widget import NapariPlotWidget
from napari_plot.utils.utilities import connect

__all__ = ["ScatterPlotWidget"]


class ScatterPlotWidget(NapariPlotWidget):
    """Widget which enables displaying scatter plot of two layers.

    If the number of points is unequal, the longer array is truncated so it has the same size and shape as the other
    data.
    """

    def __init__(self, napari_viewer: "napari.viewer.Viewer"):
        super().__init__(napari_viewer)
        self.connect_events()
        # create layer which will be used to display the data
        self.scatter_layer = self.viewer_plot.add_scatter(None, edge_color="orange")
        self.layers = []  # empty

        # get two layers
        with suppress(IndexError):
            layers = self.viewer.layers[-2:]
            if self._check_layers(layers):
                self.layers = layers
                self.on_update_scatter()

    @property
    def current_z(self) -> int:
        """Current z-step of the viewer."""
        return self.viewer.dims.current_step[0]

    @staticmethod
    def _check_layers(layers: ty.List) -> bool:
        """Check whether layers of correct type."""
        if len(layers) != 2:
            return False
        elif any([type(layer) != Image for layer in layers]):
            return False
        return True

    def on_update_layers(self, event=None):
        """Update layer selection."""
        # Update current layer when selection changed in viewer
        layers = self.viewer.layers.selection
        if self._check_layers(layers):
            self.layers = list(layers)
            self.on_update_scatter()

    def on_update_scatter(self):
        """
        Clear the axes and scatter the currently selected layers.
        """
        if self.isVisible() and self.layers and len(self.layers) == 2:
            z = self.current_z
            data = [layer.data[z].ravel() for layer in self.layers]
            sizes = [len(d) for d in data]
            if sizes[0] != sizes[1]:
                min_size = min(sizes)
                data = [d[:min_size] for d in data]
                warn("napari-plot(Scatter): The two input arrays were of different size and shape.")

            self.scatter_layer.data = np.c_[data[1], data[0]]
            self.viewer_plot.axis.x_label = self.layers[0].name
            self.viewer_plot.axis.y_label = self.layers[1].name
            self.viewer_plot.text_overlay.text = f"z={z}"

    def connect_events(self, state: bool = True) -> None:
        """Connect events."""
        connect(self.viewer.dims.events.current_step, self.on_update_scatter, state=state)
        connect(self.viewer.layers.selection.events.changed, self.on_update_layers, state=state)

    def closeEvent(self, event) -> None:
        """Close event."""
        self.connect_events(False)
        super().closeEvent(event)
