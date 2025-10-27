from __future__ import annotations

from functools import lru_cache
from itertools import chain

from napari._qt._qapp_model.injection._qprocessors import QPROCESSORS

from napari_plot._qt._qapp_model._qproviders import QPROVIDERS

# Submodules should be able to import from most modules, so to
# avoid circular imports, don't import submodules at the top level here,
# import them inside the init_qactions function.


@lru_cache  # only call once
def init_qactions() -> None:
    """Initialize all Qt-based Actions with app-model.

    This function will be called in _QtMainWindow.__init__().  It should only
    be called once (hence the lru_cache decorator).

    It is responsible for:
    - injecting Qt-specific names into the application injection_store namespace
      (this is what allows functions to be declared with annotations like
      `def foo(window: Window)` or `def foo(qt_viewer: QtViewer)`)
    - registering provider functions for the names added to the namespace
    - registering Qt-dependent actions with app-model (i.e. Q_*_ACTIONS actions).
    """
    from napari._app_model import get_app_model
    from napari._qt._qapp_model.qactions._layers_actions import LAYERS_ACTIONS
    from napari._qt.qt_main_window import Window

    from napari_plot._qt.qt_viewer import QtViewer
    from napari_plot.viewer import Viewer

    # update the namespace with the Qt-specific types/providers/processors
    app = get_app_model()
    store = app.injection_store
    store.namespace = {
        **store.namespace,
        "Viewer": Viewer,
        "Window": Window,
        "QtViewer": QtViewer,
    }

    # Qt-specific providers/processors
    app.injection_store.register(providers=QPROVIDERS)
    app.injection_store.register(processors=QPROCESSORS)

    # register menubar actions
    app.register_actions(chain(LAYERS_ACTIONS))


def reset_default_keymap():
    """Reset default keymap."""
    from napari.settings import get_settings
    from napari.utils.shortcuts import default_shortcuts

    default_shortcuts.clear()

    settings = get_settings()
    settings.shortcuts.shortcuts = default_shortcuts
