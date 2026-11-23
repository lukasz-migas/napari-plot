"""Display controls shared by the standalone and embedded plot toolbars."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qtextra.helpers import make_menu, make_menu_item
from qtpy.QtCore import QObject, QPoint

if TYPE_CHECKING:
    from collections.abc import Callable

    from napari.components.overlays import LayerNameOverlay
    from napari.layers import Layer
    from napari.utils.events import Event
    from qtextra.widgets.qt_toolbar_mini import QtMiniToolbar
    from qtpy.QtWidgets import QMenu

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
            tooltip="Show/hide plot colorbar. Right-click for colorbar options.",
            checkable=True,
            check=viewer.colorbar.visible,
            func=self._toggle_colorbar,
            func_menu=self._show_colorbar_menu,
        )
        self.colorbar_menu = make_menu(self.colorbar_btn)
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

    def _show_colorbar_menu(self, position: QPoint) -> None:
        self.colorbar_menu.deleteLater()
        self.colorbar_menu = make_menu(self.colorbar_btn)
        viewer = self._viewer
        self._populate_colorbar_menu(self.colorbar_menu, None, list(viewer.layers))
        if viewer.canvas.grid.enabled:
            for cell, indices in viewer.canvas.grid.iter_viewboxes(viewer.layers):
                if indices:
                    row, col = cell
                    menu = make_menu(self.colorbar_menu, f"Cell {row + 1}, {col + 1}", menu=self.colorbar_menu)
                    self._populate_colorbar_menu(menu, cell, [viewer.layers[index] for index in indices])
        self.colorbar_menu.popup(self.colorbar_btn.mapToGlobal(position))

    def _populate_colorbar_menu(self, menu: QMenu, cell: tuple[int, int] | None, layers: list[Layer]) -> None:
        viewer = self._viewer
        current = viewer.colorbar if cell is None else viewer._cell_colorbars.get(cell)

        def update(name: str, value: object) -> None:
            colorbar = viewer.colorbar if cell is None else viewer.colorbar_for_cell(*cell)
            setattr(colorbar, name, value)

        make_menu_item(
            menu,
            "Visible",
            menu=menu,
            checkable=True,
            checked=bool(current and current.visible),
            func=lambda checked: update("visible", checked),
        )
        make_menu_item(
            menu,
            "Right",
            menu=menu,
            checkable=True,
            checked=current is None or current.position == "right",
            func=lambda: update("position", "right"),
        )
        make_menu_item(
            menu,
            "Bottom",
            menu=menu,
            checkable=True,
            checked=bool(current and current.position == "bottom"),
            func=lambda: update("position", "bottom"),
        )
        make_menu_item(
            menu,
            "Logarithmic scale",
            menu=menu,
            checkable=True,
            checked=bool(current and current.norm == "log"),
            func=lambda checked: update("norm", "log" if checked else "linear"),
        )
        sources = [layer for layer in layers if viewer._colorbar_events(layer)]
        if sources:
            source_menu = make_menu(menu, "Follow layer", menu=menu)
            for layer in sources:
                make_menu_item(
                    source_menu,
                    layer.name,
                    menu=source_menu,
                    checkable=True,
                    checked=viewer._colorbar_sources.get(cell) is layer,
                    func=lambda _checked=False, source=layer: viewer.set_colorbar_from_layer(
                        source, current.label if current else "", cell=cell
                    ),
                )
