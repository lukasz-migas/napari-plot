"""Regression tests for native napari layer-list context expressions."""

import numpy as np
from napari._app_model.actions._layerlist_context_actions import (
    LAYERLIST_CONTEXT_ACTIONS,
    LAYERLIST_CONTEXT_SUBMENUS,
)
from napari._app_model.context import get_context
from napari.layers.base import LayerLock

from napari_plot.components.viewer_model import ViewerModel


def _evaluate_layer_context_menu(viewer: ViewerModel) -> None:
    """Evaluate the native context-menu expressions against napari-plot state."""
    context = get_context(viewer.layers)
    for action in LAYERLIST_CONTEXT_ACTIONS:
        if action.enablement is not None:
            action.enablement.eval(context)
        for menu_rule in action.menus or ():
            if menu_rule.when is not None:
                menu_rule.when.eval(context)
    for _, submenu in LAYERLIST_CONTEXT_SUBMENUS:
        if submenu.when is not None:
            submenu.when.eval(context)
        if submenu.enablement is not None:
            submenu.enablement.eval(context)


def test_native_layer_context_menu_supports_deletion_lock() -> None:
    """Right-click conditions include napari 0.8's deletion-lock context key."""
    viewer = ViewerModel()
    layer = viewer.add_image(np.zeros((2, 2)))

    _evaluate_layer_context_menu(viewer)

    layer.locked = LayerLock.DELETION
    _evaluate_layer_context_menu(viewer)
