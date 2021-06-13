"""Layer list"""
from napari.components.layerlist import LayerList as _LayerList


class LayerList(_LayerList):
    """Monkey-patched layer list"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def toggle_selected_editable(self):
        """Toggle editable of selected layers"""
        for layer in self:
            if layer.selected:
                layer.editable = not layer.editable

    def remove_all(self):
        """Remove all layers"""
        self.select_all()
        self.remove_selected()
