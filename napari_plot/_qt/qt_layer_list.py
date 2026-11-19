"""Plot layer icons and context menus scoped to the clicked plot."""

from __future__ import annotations

from napari._app_model import get_app_model
from napari._qt.containers import QtLayerList as NapariQtLayerList
from napari._qt.containers._base_item_model import ItemRole
from napari._qt.containers._layer_delegate import LayerDelegate
from napari._qt.qt_resources import QColoredSVGIcon
from napari.components import LayerList
from napari.layers import Layer
from napari.utils.theme import get_theme
from qtextra.helpers import make_qta_icon
from qtpy.QtCore import QModelIndex, QPoint, QSize, QSortFilterProxyModel
from qtpy.QtGui import QPalette
from qtpy.QtWidgets import QStyleOptionViewItem, QWidget

from napari_plot.resources import ICONS

_LAYER_ICONS = {
    "areas": "mdi.chart-areaspline",
    "band": "mdi.chart-bell-curve",
    "bar": "ri.bar-chart-fill",
    "centroids": "new_centroids",
    "errorbar": "mdi.chart-box-outline",
    "infline": "new_inf_line",
    "line": "new_line",
    "multiline": "new_line",
    "rectangles": "mdi6.vector-rectangle",
    "region": "new_region",
    "scatter": "new_scatter",
    "text": "mdi.format-text",
}


class _LayerDelegate(LayerDelegate):
    """Draw plot icons and provide the clicked layer list to native actions."""

    def get_layer_icon(self, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Set the type decoration using plot assets or napari's native lookup."""
        layer: Layer | None = index.data(ItemRole)
        if layer is None:
            return
        icon_name = _LAYER_ICONS.get(layer._type_string)
        if icon_name is None:
            super().get_layer_icon(option, index)
            return

        background = option.palette.color(QPalette.ColorRole.Window)
        color = get_theme("dark" if background.red() < 128 else "light").icon.as_hex()
        if svg_path := ICONS.get(icon_name):
            option.icon = QColoredSVGIcon(svg_path, color=color)
        else:
            option.icon = make_qta_icon(icon_name, color=color, color_active=color, color_selected=color)
        option.decorationSize = QSize(18, 18)
        option.decorationPosition = QStyleOptionViewItem.Position.Right
        option.features |= QStyleOptionViewItem.ViewItemFeature.HasDecoration

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
