"""Display controls shared by the standalone and embedded plot toolbars."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qtextra.helpers import make_menu, make_menu_item
from qtpy.QtCore import QObject, QPoint

if TYPE_CHECKING:
    from collections.abc import Callable

    from napari.components.overlays import LayerNameOverlay
    from napari.utils.events import Event
    from qtextra.widgets.qt_toolbar_mini import QtMiniToolbar

    from napari_plot.components.viewer_model import ViewerModel


class QtPlotDisplayControls(QObject):
    """Add grid layout, layer label, and colorbar toggles to a plot toolbar."""

    def __init__(
        self,
        toolbar: QtMiniToolbar,
        viewer: ViewerModel,
        *,
        open_grid_settings: Callable[[], None] | None = None,
        open_label_settings: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(toolbar)
        self._viewer = viewer
        self._name_overlays: set[LayerNameOverlay] = set()
        self.grid_btn = toolbar.add_qta_tool(
            "mdi6.grid-off",
            tooltip="Toggle tiled grid view. Right-click for grid options.",
            checkable=True,
            check=viewer.canvas.grid.enabled,
            func=self._toggle_grid,
            func_menu=self._show_grid_menu,
        )
        self.grid_btn.set_toggle_qta("mdi6.grid-off", "mdi6.grid")
        self.grid_menu = make_menu(self.grid_btn)
        self.group_by_metadata_action = make_menu_item(
            self.grid_btn, "Group by layer metadata", menu=self.grid_menu, checkable=True
        )
        self.group_by_metadata_action.toggled.connect(self._toggle_group_by_metadata)
        self.grid_menu.aboutToShow.connect(self._sync_group_by_metadata)
        if open_grid_settings is not None:
            self.grid_menu.addSeparator()
            make_menu_item(self.grid_btn, "Grid Settings...", menu=self.grid_menu, func=open_grid_settings)
        viewer.canvas.grid.events.connect(self._sync_group_by_metadata)
        self._sync_group_by_metadata()
        self.layer_labels_btn = toolbar.add_qta_tool(
            "mdi6.label-multiple",
            tooltip="Show/hide layer labels.",
            checkable=True,
            func=self._toggle_layer_labels,
            func_menu=open_label_settings,
        )
        self.colorbar_btn = toolbar.add_qta_tool(
            "colorbar",
            tooltip="Show/hide plot colorbar.",
            checkable=True,
            check=viewer.colorbar.visible,
            func=self._toggle_colorbar,
        )
        viewer.canvas.grid.events.enabled.connect(self._sync_grid)
        viewer.colorbar.events.visible.connect(self._sync_colorbar)
        viewer.layers.events.inserted.connect(self._refresh_layer_labels)
        viewer.layers.events.removed.connect(self._refresh_layer_labels)
        viewer.layers.events.changed.connect(self._refresh_layer_labels)
        self._refresh_layer_labels()

    def _show_grid_menu(self, position: QPoint) -> None:
        self.grid_menu.popup(self.grid_btn.mapToGlobal(position))

    def _toggle_group_by_metadata(self, enabled: bool) -> None:
        self._viewer.canvas.grid.group_by_metadata = enabled

    def _sync_group_by_metadata(self, _event: Event | None = None) -> None:
        self.group_by_metadata_action.setChecked(self._viewer.canvas.grid.group_by_metadata)

    def _toggle_grid(self, enabled: bool) -> None:
        self._viewer.canvas.grid.enabled = enabled

    def _sync_grid(self, _event: Event | None = None) -> None:
        # read state from the model; napari 0.10 overlays emit plain values rather than ``Event`` objects
        self.grid_btn.setChecked(self._viewer.canvas.grid.enabled)

    def _toggle_layer_labels(self, visible: bool) -> None:
        for overlay in self._name_overlays:
            overlay.visible = visible

    def _refresh_layer_labels(self, _event: Event | None = None) -> None:
        overlays = {layer.name_overlay for layer in self._viewer.layers}
        for overlay in self._name_overlays - overlays:
            overlay.events.visible.disconnect(self._sync_layer_labels)
        for overlay in overlays - self._name_overlays:
            overlay.events.visible.connect(self._sync_layer_labels)
        self._name_overlays = overlays
        self.layer_labels_btn.setEnabled(bool(overlays))
        self._sync_layer_labels()

    def _sync_layer_labels(self, _event: Event | None = None) -> None:
        self.layer_labels_btn.setChecked(
            bool(self._name_overlays) and all(overlay.visible for overlay in self._name_overlays)
        )

    def _toggle_colorbar(self, visible: bool) -> None:
        self._viewer.colorbar.visible = visible

    def _sync_colorbar(self, _event: Event | None = None) -> None:
        self.colorbar_btn.setChecked(self._viewer.colorbar.visible)
