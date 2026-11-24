"""Image histogram whose shaded span is linked to the layer's contrast limits."""

from __future__ import annotations

import typing as ty

import numpy as np
import qtextra.helpers as hp
from napari.layers import Image

from napari_plot._layer_sampling import image_plane, layer_color
from napari_plot._profile_widget import HostPlotWidget

if ty.TYPE_CHECKING:
    import napari

__all__ = ["HistogramWidget"]


class HistogramWidget(HostPlotWidget):
    """Histogram of the displayed plane of the active image layer, linked to its contrast limits.

    The shaded span shows the contrast limits. Moving or editing the span in the plot (select it, then use the
    region move or edit mode) updates the image's contrast limits, and changing the limits in napari moves the
    span.
    """

    def __init__(self, napari_viewer: napari.viewer.Viewer) -> None:
        super().__init__(napari_viewer)
        self.image_layer: Image | None = None
        self._syncing = False

        self.bins = hp.make_int_spin_box(
            self, minimum=2, maximum=4096, default=128, tooltip="Number of histogram bins", func=self.update_histogram
        )
        self.log_scale = hp.make_checkbox(self, "Log counts", tooltip="Use a logarithmic count axis", func=self._on_log)
        self.add_controls(
            hp.make_h_layout(
                hp.make_label(self, "Bins"), self.bins, self.log_scale, stretch_after=True, margin=(6, 6, 6, 0)
            )
        )
        self.viewer_plot.axis.x_label = "Intensity"
        self.viewer_plot.axis.y_label = "Count"

        self.limits = self.viewer_plot.axvspan(0, 1, name="Contrast limits", opacity=0.3)
        self.limits.visible = False
        self.limits.selected_data = {0}
        self.limits.mode = "move"
        self.limits.events.data.connect(self._on_limits_moved)

        self.connect_host(self.viewer.layers.selection.events.active, self._on_active_layer)
        self.connect_host(self.viewer.layers.events.removed, self._on_layer_removed)
        self.connect_host(self.viewer.dims.events.current_step, self.update_histogram)
        self._on_active_layer()
        if self.image_layer is None:
            images = [layer for layer in self.viewer.layers if isinstance(layer, Image)]
            self.set_image_layer(images[-1] if images else None)

    def set_image_layer(self, layer: Image | None) -> None:
        """Show the histogram and contrast limits of ``layer``."""
        if self.image_layer is not None:
            self.disconnect_host(self.image_layer.events.contrast_limits)
            self.disconnect_host(self.image_layer.events.data)
        self.image_layer = layer
        if layer is not None:
            self.connect_host(layer.events.contrast_limits, self._on_contrast_limits)
            self.connect_host(layer.events.data, self.update_histogram)
        self.update_histogram()
        self._on_contrast_limits()

    def _on_active_layer(self, event: ty.Any = None) -> None:
        active = self.viewer.layers.selection.active
        if isinstance(active, Image) and active is not self.image_layer:
            self.set_image_layer(active)

    def _on_layer_removed(self, event: ty.Any = None) -> None:
        if self.image_layer is not None and self.image_layer not in self.viewer.layers:
            self.set_image_layer(None)

    def _on_log(self, state: ty.Any = None) -> None:
        self.viewer_plot.axis.y_scale = "log" if self.log_scale.isChecked() else "linear"
        self.update_histogram()

    def histogram(self) -> tuple[np.ndarray, np.ndarray] | None:
        """Return the step outline ``xy`` of the histogram and the bin counts, or None without a usable image."""
        layer = self.image_layer
        if layer is None:
            return None
        try:
            plane, _ = image_plane(layer, self.viewer.dims)
        except ValueError:
            return None
        values = plane[np.isfinite(plane)]
        if values.size == 0:
            return None
        low, high = (float(value) for value in layer.contrast_limits_range)
        low, high = min(low, float(values.min())), max(high, float(values.max()))
        if high <= low:
            high = low + 1
        counts, edges = np.histogram(values, bins=self.bins.value(), range=(low, high))
        counts = counts.astype(float)
        if self.log_scale.isChecked():
            # empty bins have no position on a log axis, so draw them just below one count
            counts[counts == 0] = 0.5
        # draw as steps: every bin contributes its left and right edge at its count
        x = np.repeat(edges, 2)[1:-1]
        y = np.repeat(counts, 2)
        return np.column_stack((x, y)), counts

    def update_histogram(self, event: ty.Any = None) -> None:
        """Recompute the histogram of the displayed plane."""
        result = self.histogram()
        if result is None:
            self.set_series({})
            self.limits.visible = False
            if self.image_layer is None:
                self.viewer_plot.text_overlay.text = "Select an image layer"
            else:
                self.viewer_plot.text_overlay.text = f"Cannot show a histogram of '{self.image_layer.name}'"
            return
        xy, _ = result
        self.set_series({self.image_layer.name: (xy, layer_color(self.image_layer))})
        self.limits.visible = True
        self.viewer_plot.text_overlay.text = ""

    def _on_contrast_limits(self, event: ty.Any = None) -> None:
        """Move the span to the image's contrast limits."""
        if self.image_layer is None or self._syncing:
            return
        self._syncing = True
        try:
            self.limits.data = [[float(value) for value in self.image_layer.contrast_limits]]
            self.limits.selected_data = {0}
        finally:
            self._syncing = False

    def _on_limits_moved(self, event: ty.Any = None) -> None:
        """Apply the span to the image's contrast limits."""
        if self.image_layer is None or self._syncing or len(self.limits.data) == 0:
            return
        low, high = sorted(float(value) for value in self.limits.data[0])
        if high <= low:
            return
        self._syncing = True
        try:
            self.image_layer.contrast_limits = (low, high)
        finally:
            self._syncing = False

    def closeEvent(self, event: ty.Any) -> None:
        """Disconnect the span before closing."""
        self.limits.events.data.disconnect(self._on_limits_moved)
        super().closeEvent(event)
