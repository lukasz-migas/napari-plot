"""Layer list"""

from napari.components.layerlist import LayerList as _LayerList


class LayerList(_LayerList):
    """Monkey-patched layer list"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create_contexts(self):
        """Create contexts to manage enabled/visible action/menu states.

        Connects LayerList and Selection[Layer] to their context keys to allow
        actions and menu items (in the GUI) to be dynamically enabled/disabled
        and visible/hidden based on the state of layers in the list.
        """

        # TODO: figure out how to move this context creation bit.
        # Ideally, the app should be aware of the layerlist, but not vice versa.
        # This could probably be done by having the layerlist emit events that
        # the app connects to, then the `_ctx` object would live on the app,
        # (not here)
        from napari_plot._app_model.context import create_context
        from napari_plot._app_model.context._layerlist_context import (
            LayerListContextKeys,
            LayerListSelectionContextKeys,
        )

        self._ctx = create_context(self)
        if self._ctx is not None:  # happens during Viewer type creation
            self._ctx_keys = LayerListContextKeys(self._ctx)
            self.events.inserted.connect(self._ctx_keys.update)
            self.events.removed.connect(self._ctx_keys.update)

            self._selection_ctx_keys = LayerListSelectionContextKeys(self._ctx)
            self.selection.events.changed.connect(self._selection_ctx_keys.update)

    def toggle_selected_editable(self):
        """Toggle editable of selected layers"""
        for layer in self:
            if layer.selected:
                layer.editable = not layer.editable

    def remove_all(self):
        """Remove all layers"""
        self.select_all()
        self.remove_selected()
