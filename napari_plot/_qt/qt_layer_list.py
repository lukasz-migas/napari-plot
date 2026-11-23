"""Plot layer icons and context menus scoped to the clicked plot."""

from __future__ import annotations

from functools import partial
from typing import Any

from app_model.backends.qt import QModelMenu
from napari._app_model import get_app_model
from napari._app_model.constants import MenuId
from napari._app_model.context import get_context
from napari._qt._qapp_model import build_qmodel_menu
from napari._qt.containers import QtLayerList as NapariQtLayerList, QtLayerListModel
from napari._qt.containers._base_item_model import ItemRole
from napari._qt.containers._layer_delegate import LayerDelegate
from napari._qt.containers.qt_layer_model import ThumbnailRole
from napari._qt.qt_resources import QColoredSVGIcon
from napari.components import LayerList
from napari.layers import Layer
from napari.utils.theme import get_theme
from qtextra.helpers import get_text, make_menu, make_menu_item, make_qta_icon, warn
from qtpy.QtCore import QModelIndex, QPersistentModelIndex, QPoint, QSize, QSortFilterProxyModel, Qt
from qtpy.QtGui import QPalette
from qtpy.QtWidgets import QStyleOptionViewItem, QWidget

from napari_plot.layers._grouping import LAYER_GROUP_KEY, get_layer_group
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


def _set_group(layers: tuple[Layer, ...], group: str | None) -> None:
    """Set or clear membership and notify listeners through the metadata setter."""
    for layer in layers:
        if get_layer_group(layer) == group:
            continue
        metadata = layer.metadata.copy()
        if group is None:
            metadata.pop(LAYER_GROUP_KEY, None)
        else:
            metadata[LAYER_GROUP_KEY] = group
        layer.metadata = metadata


def _create_group(parent: QWidget, layer_list: LayerList, selected: tuple[Layer, ...]) -> None:
    """Prompt for a new group name and assign it to the selected layers."""
    group = (get_text(parent, label="Group name", title="Group Layers") or "").strip()
    if not group:
        return
    if any(get_layer_group(layer) == group for layer in layer_list):
        warn(parent, 'That group already exists. Use "Add to Group" to join it.', title="Group Layers")
        return
    _set_group(selected, group)


def _add_group_actions(menu: QModelMenu, layer_list: LayerList, parent: QWidget) -> None:
    """Add grouping commands for this layer list's current selection."""
    selected = tuple(layer_list.selection)
    groups = sorted({group for layer in layer_list if (group := get_layer_group(layer)) is not None})
    menu.addSeparator()
    make_menu_item(
        menu,
        "Group Layers…",
        menu=menu,
        func=partial(_create_group, parent, layer_list, selected),
        disabled=len(selected) < 2,
    ).setObjectName("napari_plot.layer.group")
    existing = make_menu(menu, "Add to Group", menu=menu)
    existing.menuAction().setObjectName("napari_plot.layer.add_to_group")
    existing.setEnabled(bool(selected and groups))
    for group in groups:
        make_menu_item(
            existing, group.replace("&", "&&"), menu=existing, func=partial(_set_group, selected, group)
        ).setObjectName(f"napari_plot.layer.add_to_group.{group}")
    make_menu_item(
        menu,
        "Ungroup Layers",
        menu=menu,
        func=partial(_set_group, selected, None),
        disabled=all(get_layer_group(layer) is None for layer in selected),
    ).setObjectName("napari_plot.layer.ungroup")


class _LayerListModel(QtLayerListModel):
    """Expose group membership and thumbnails with Qt-owned pixel storage."""

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return row data, with group membership in the tooltip."""
        value = super().data(index, role)
        if role == Qt.ItemDataRole.ToolTipRole and index.isValid():
            group = get_layer_group(self.getItemStrict(index))
            if group is not None:
                return f"{value}\nGroup: {group}"
        if role == ThumbnailRole and value is not None:
            # PyQt can release the source image's Python buffer during QVariant conversion.
            return value.copy()
        return value


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
        """Open the native menu with grouping for the clicked plot's layers."""
        layer_list: LayerList = model.sourceModel()._root
        # Prefer the clicked plot over providers for the active napari window.
        with get_app_model().injection_store.register(
            providers=[
                (lambda: layer_list, LayerList, 1),
                (lambda: layer_list.selection.active, Layer, 1),
            ]
        ):
            menu = build_qmodel_menu(MenuId.LAYERLIST_CONTEXT, parent=parent)
            try:
                menu.update_from_context(get_context(layer_list))
                _add_group_actions(menu, layer_list, parent)
                menu.exec(pos)
            finally:
                menu.deleteLater()


class QtLayerList(NapariQtLayerList):
    """Keep native layer-list behavior with plot-aware context-menu actions."""

    def __init__(self, root: LayerList, parent: QWidget | None = None) -> None:
        super().__init__(root, parent)
        previous_delegate = self.itemDelegate()
        delegate = _LayerDelegate(self)
        self.setItemDelegate(delegate)
        delegate.loading_frame_changed.connect(self.viewport().update)
        previous_delegate.deleteLater()

    def setRoot(self, root: LayerList) -> None:
        """Bind the layer list to the thumbnail model and sync its selection."""
        self._root = root
        self.setModel(_LayerListModel(root, self))
        root.selection.events.changed.connect(self._on_py_selection_change)
        root.selection.events._current.connect(self._on_py_current_change)
        self._sync_selection_models()
