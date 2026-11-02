"""Layer list with context-menu providers scoped to the clicked plot."""

from __future__ import annotations

from napari._app_model import get_app_model
from napari._qt.containers import QtLayerList as NapariQtLayerList
from napari._qt.containers._layer_delegate import LayerDelegate
from napari.components import LayerList
from napari.layers import Layer
from qtpy.QtCore import QModelIndex, QPoint, QSortFilterProxyModel
from qtpy.QtWidgets import QWidget


class _LayerDelegate(LayerDelegate):
    """Provide the clicked layer list while native menu actions are evaluated."""

    def show_context_menu(
        self,
        index: QModelIndex,
        model: QSortFilterProxyModel,
        pos: QPoint,
        parent: QWidget,
    ) -> None:
        """Open the native menu with providers for the clicked plot's layers."""
        layer_list: LayerList = model.sourceModel()._root
        # Prefer the clicked plot over providers for the active napari window.
        with get_app_model().injection_store.register(
            providers=[
                (lambda: layer_list, LayerList, 1),
                (lambda: layer_list.selection.active, Layer, 1),
            ]
        ):
            super().show_context_menu(index, model, pos, parent)


class QtLayerList(NapariQtLayerList):
    """Keep native layer-list behavior with plot-aware context-menu actions."""

    def __init__(self, root: LayerList, parent: QWidget | None = None) -> None:
        super().__init__(root, parent)
        previous_delegate = self.itemDelegate()
        delegate = _LayerDelegate(self)
        self.setItemDelegate(delegate)
        delegate.loading_frame_changed.connect(self.viewport().update)
        previous_delegate.deleteLater()
