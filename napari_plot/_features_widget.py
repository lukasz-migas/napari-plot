"""Scatter plot of a napari layer's ``features`` table, with selections linked between plot and layer."""

from __future__ import annotations

import typing as ty

import numpy as np
import qtextra.helpers as hp
from napari.layers import Labels, Points, Shapes

from napari_plot._profile_widget import HostPlotWidget

if ty.TYPE_CHECKING:
    import napari
    import pandas as pd
    from napari.layers import Layer

__all__ = ["FeaturesPlotWidget"]

ROW_INDEX = "<row index>"


def _has_features(layer: Layer) -> bool:
    features = getattr(layer, "features", None)
    return features is not None and len(features.columns) > 0


class FeaturesPlotWidget(HostPlotWidget):
    """Scatter plot of two feature columns of a Points, Shapes, Labels or other layer with ``features``.

    The widget follows the most recently selected layer that has features. Selecting markers in the plot (box,
    lasso or polygon selection) selects the matching points or shapes in napari, or, for Labels, the first
    matching label. Selecting points or shapes in napari highlights their markers in the plot.
    """

    def __init__(self, napari_viewer: napari.viewer.Viewer) -> None:
        super().__init__(napari_viewer)
        self.source_layer: Layer | None = None
        self._syncing = False

        self.x_choice = hp.make_combobox(self, tooltip="Feature on the x-axis", func=self.update_plot)
        self.y_choice = hp.make_combobox(self, tooltip="Feature on the y-axis", func=self.update_plot)
        self.add_controls(
            hp.make_h_layout(
                hp.make_label(self, "x"),
                self.x_choice,
                hp.make_label(self, "y"),
                self.y_choice,
                stretch_id=(1, 3),
                margin=(6, 6, 6, 0),
            )
        )
        self.scatter_layer = self.viewer_plot.add_scatter(None, name="Features", face_color="#1f77b4")
        self.viewer_plot.events.selection.connect(self._on_plot_selection)

        self.connect_host(self.viewer.layers.selection.events.active, self._on_active_layer)
        self.connect_host(self.viewer.layers.events.removed, self._on_layer_removed)
        self._on_active_layer()
        if self.source_layer is None:
            layers = [layer for layer in self.viewer.layers if _has_features(layer)]
            self.set_source_layer(layers[-1] if layers else None)

    @property
    def features(self) -> pd.DataFrame | None:
        """Features table of the source layer."""
        return None if self.source_layer is None else self.source_layer.features

    def set_source_layer(self, layer: Layer | None) -> None:
        """Plot the features of ``layer``."""
        if self.source_layer is not None:
            for name in ("features", "data", "highlight", "selected_label"):
                if hasattr(self.source_layer.events, name):
                    self.disconnect_host(getattr(self.source_layer.events, name))
        self.source_layer = layer
        if layer is not None:
            for name, callback in (
                ("features", self._update_columns),
                ("data", self._update_columns),
                ("highlight", self._on_host_selection),
                ("selected_label", self._on_host_selection),
            ):
                if hasattr(layer.events, name):
                    self.connect_host(getattr(layer.events, name), callback)
        self._update_columns()

    def _on_active_layer(self, event: ty.Any = None) -> None:
        active = self.viewer.layers.selection.active
        if active is not None and active is not self.source_layer and _has_features(active):
            self.set_source_layer(active)

    def _on_layer_removed(self, event: ty.Any = None) -> None:
        if self.source_layer is not None and self.source_layer not in self.viewer.layers:
            self.set_source_layer(None)

    def _columns(self) -> list[str]:
        features = self.features
        if features is None:
            return []
        from pandas.api.types import is_bool_dtype, is_numeric_dtype

        numeric = [
            str(name)
            for name in features.columns
            if is_numeric_dtype(features[name]) and not is_bool_dtype(features[name])
        ]
        return [ROW_INDEX, *numeric]

    def _update_columns(self, event: ty.Any = None) -> None:
        columns = self._columns()
        current = (self.x_choice.currentText(), self.y_choice.currentText())
        defaults = (columns[1], columns[2]) if len(columns) > 2 else (ROW_INDEX, columns[-1] if columns else "")
        for choice, previous, default in zip((self.x_choice, self.y_choice), current, defaults, strict=True):
            hp.combobox_setter(choice, items=columns, set_item=previous if previous in columns else default)
        self.update_plot()

    def _values(self, column: str) -> np.ndarray:
        features = self.features
        if features is None or (column != ROW_INDEX and column not in features.columns):
            return np.empty(0)
        if column == ROW_INDEX:
            return np.arange(len(features), dtype=float)
        return np.asarray(features[column], dtype=float)

    def update_plot(self, event: ty.Any = None) -> None:
        """Redraw the scatter plot from the chosen feature columns."""
        x_name, y_name = self.x_choice.currentText(), self.y_choice.currentText()
        x, y = self._values(x_name), self._values(y_name)
        self._syncing = True
        try:
            self.scatter_layer.data = np.column_stack((y, x)) if len(x) == len(y) else np.empty((0, 2))
        finally:
            self._syncing = False
        self.viewer_plot.axis.x_label = x_name
        self.viewer_plot.axis.y_label = y_name
        if self.source_layer is None:
            self.viewer_plot.text_overlay.text = "Select a layer with features"
        elif len(self._columns()) < 2:
            self.viewer_plot.text_overlay.text = f"'{self.source_layer.name}' has no numeric features"
        else:
            self.viewer_plot.text_overlay.text = ""
        self._on_host_selection()

    def _label_values(self) -> np.ndarray:
        """Label value of each features row (the ``index`` column, or the row number)."""
        features = self.features
        if features is None:
            return np.empty(0, dtype=int)
        if "index" in features.columns:
            return np.asarray(features["index"], dtype=int)
        return np.arange(len(features))

    def _on_plot_selection(self, event: ty.Any) -> None:
        """Push rows selected in the plot to the source layer."""
        if self.scatter_layer not in event.value or self.source_layer is None:
            return
        self.select_rows(event.value[self.scatter_layer])

    def select_rows(self, rows: ty.Iterable[int]) -> None:
        """Select features rows in the source layer (points, shapes, or the first matching label)."""
        rows = sorted(int(row) for row in rows)
        layer = self.source_layer
        self._syncing = True
        try:
            if isinstance(layer, (Points, Shapes)):
                layer.selected_data = set(rows)
            elif isinstance(layer, Labels) and rows:
                layer.selected_label = int(self._label_values()[rows[0]])
        finally:
            self._syncing = False
        self.scatter_layer.selected_data = rows

    def _on_host_selection(self, event: ty.Any = None) -> None:
        """Highlight the markers of the rows selected in the source layer."""
        if self._syncing:
            return
        layer = self.source_layer
        rows: set[int] = set()
        if isinstance(layer, (Points, Shapes)):
            rows = set(layer.selected_data)
        elif isinstance(layer, Labels):
            rows = set(np.flatnonzero(self._label_values() == layer.selected_label).tolist())
        rows = {row for row in rows if row < len(self.scatter_layer.data)}
        if rows != self.scatter_layer.selected_data:
            self.scatter_layer.selected_data = rows

    def closeEvent(self, event: ty.Any) -> None:
        """Disconnect plot selection before closing."""
        self.viewer_plot.events.selection.disconnect(self._on_plot_selection)
        super().closeEvent(event)
