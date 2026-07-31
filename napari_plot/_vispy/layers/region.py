"""Region layer"""

import typing as ty

import numpy as np
from napari._vispy.layers.base import VispyBaseLayer

from napari_plot._vispy.visuals.region import RegionVisual

if ty.TYPE_CHECKING:
    from napari_plot.layers import Region


class VispyRegionLayer(VispyBaseLayer):
    """Infinite region layer"""

    layer: "Region"
    node: RegionVisual

    def __init__(self, layer: "Region", font_info) -> None:
        node = RegionVisual()
        super().__init__(layer, node, font_info=font_info)
        self.node.opacity = layer.opacity

        # connect events
        self.layer.events.color.connect(self._on_appearance_change)
        self.layer.events.highlight.connect(self._on_highlight_change)
        self.layer.events.adding.connect(self._on_adding_change)
        self.layer.events.removed.connect(self._on_remove_change)

        self.reset()
        self._on_data_change()

    def _on_adding_change(self, _event=None) -> None:
        """Update the temporary region shown while adding a new region."""
        # update temporary
        pos, orientation = self.layer._creating_value
        color = self.layer.current_color
        if color.ndim == 2:
            color = color[0]
        if pos is not None:
            if orientation == "vertical":
                self.node.vertical_visual.set_data(pos=pos, color=color)
                self.node.horizontal_visual.set_data(color=(0, 0, 0, 0))
            else:
                self.node.horizontal_visual.set_data(pos=pos, color=color)
                self.node.vertical_visual.set_data(color=(0, 0, 0, 0))
        else:
            self.node.vertical_visual.set_data(color=(0, 0, 0, 0))
            self.node.horizontal_visual.set_data(color=(0, 0, 0, 0))

    def _on_remove_change(self, event) -> None:
        """Remove regions."""
        self._update_regions_visual()

    def _on_appearance_change(self, _event=None) -> None:
        """Change the appearance of the data."""
        self._update_regions_visual()

    def _on_data_change(self, _event=None) -> None:
        """Set data."""
        self._update_regions_visual()

    def _update_regions_visual(self) -> None:
        """Update the batched visual with current region data and highlight colors."""
        pos, orientation, color = self.layer._data_view.get_simple_lines_and_colors()
        selected = self.layer.selected_data
        if selected:
            color = color.copy()
            for index in selected:
                if index < len(color):
                    color[index] = self.layer._highlight_color
        self.node.regions_visual.set_data(
            pos=pos,
            orientation=orientation,
            color=color,
        )
        self.node.update()

    def _on_highlight_change(self, event=None) -> None:
        """Highlight."""
        # TODO: this is actually quite dumb since it will constantly update the highlight
        self._on_appearance_change()

        # Compute the location and properties of the vertices and box that need to get rendered
        edge_color, pos, width = self.layer._compute_box()

        # add region edges
        if pos is None or len(pos) == 0:
            pos = np.zeros((1, self.layer._slice_input.ndisplay))
            width = 0
        self.node.select_box.set_data(pos=pos, color=edge_color, width=width)
        self.node.update()

    def close(self) -> None:
        """Vispy visual is closing."""
        self.node.regions_visual.set_data(
            pos=np.zeros((0, 2), dtype=np.float32),
            orientation=np.zeros(0, dtype=np.float32),
            color=np.zeros((0, 4), dtype=np.float32),
        )
        super().close()
