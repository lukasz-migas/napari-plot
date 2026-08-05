"""Scatter widget.

This widget is inspired by ScatterWidget in https://github.com/dstansby/napari-matplotlib
"""

from contextlib import suppress
from typing import Any
from warnings import warn

import napari
import numpy as np
import qtextra.helpers as hp
from napari.layers import Image

from napari_plot._plot_widget import NapariPlotWidget

__all__ = ["ScatterPlotWidget"]


class ScatterPlotWidget(NapariPlotWidget):
    """Widget which enables displaying scatter plot of two layers.

    The widget compares the values in the currently displayed slices. Selected
    images must therefore have identical displayed-slice shapes.
    """

    def __init__(self, napari_viewer: "napari.viewer.Viewer"):
        super().__init__(napari_viewer)
        # create layer which will be used to display the data
        self.scatter_layer = self.viewer_plot.add_scatter(None, border_color="orange")
        self.layers: list[Image] = []
        self.connect_events()

        # get two layers
        with suppress(IndexError):
            layers = self.viewer.layers[-2:]
            if self._check_layers(layers):
                self._set_layers(layers)
                self.on_update_scatter()

    @property
    def current_slice_label(self) -> str:
        """Human-readable coordinates of the current non-displayed dimensions."""
        displayed = set(self.viewer.dims.displayed)
        coordinates = [
            f"{axis}={step}" for axis, step in enumerate(self.viewer.dims.current_step) if axis not in displayed
        ]
        return ", ".join(coordinates)

    @staticmethod
    def _check_layers(layers: list) -> bool:
        """Check whether layers of correct type."""
        return len(layers) == 2 and all(isinstance(layer, Image) for layer in layers)

    @staticmethod
    def _displayed_slice(layer: Image) -> np.ndarray:
        """Return the image values currently displayed by napari."""
        return np.asarray(layer._data_view)

    @classmethod
    def _scatter_data(cls, layers: list[Image]) -> np.ndarray:
        """Build paired scatter coordinates from two displayed image slices."""
        data = [cls._displayed_slice(layer) for layer in layers]
        if data[0].shape != data[1].shape:
            raise ValueError(
                "Selected image layers must have matching displayed-slice shapes; "
                f"received {data[0].shape} and {data[1].shape}."
            )
        return np.column_stack((data[1].ravel(), data[0].ravel()))

    def _set_layers(self, layers: list[Image]) -> None:
        """Replace selected layers and update their data-event connections."""
        for layer in self.layers:
            hp.connect(layer.events.data, self.on_update_scatter, state=False)
        self.layers = list(layers)
        for layer in self.layers:
            hp.connect(layer.events.data, self.on_update_scatter, state=True)

    def on_update_layers(self, event=None):
        """Update layer selection."""
        # Update current layer when selection changed in viewer
        layers = list(self.viewer.layers.selection)
        if self._check_layers(layers):
            self._set_layers(layers)
            self.on_update_scatter()
        else:
            self._set_layers([])
            self.scatter_layer.data = np.empty((0, 2), dtype=float)
            self.viewer_plot.text_overlay.text = "Select two image layers"

    def on_update_scatter(self, event: Any = None) -> None:
        """Update the scatter plot from the selected displayed image slices."""
        if len(self.layers) != 2:
            return
        try:
            data = self._scatter_data(self.layers)
        except ValueError as error:
            self.scatter_layer.data = np.empty((0, 2), dtype=float)
            self.viewer_plot.text_overlay.text = str(error)
            warn(f"napari-plot (Scatter): {error}", stacklevel=2)
            return

        self.scatter_layer.data = data
        self.viewer_plot.axis.x_label = self.layers[0].name
        self.viewer_plot.axis.y_label = self.layers[1].name
        self.viewer_plot.text_overlay.text = self.current_slice_label

    def connect_events(self, state: bool = True) -> None:
        """Connect events."""
        hp.connect(self.viewer.dims.events.current_step, self.on_update_scatter, state=state)
        hp.connect(
            self.viewer.layers.selection.events.changed,
            self.on_update_layers,
            state=state,
        )

    def closeEvent(self, event) -> None:
        """Close event."""
        self._set_layers([])
        self.connect_events(False)
        super().closeEvent(event)
