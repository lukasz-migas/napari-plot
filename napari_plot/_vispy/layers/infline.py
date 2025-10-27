"""Line layer"""

import typing as ty

import numpy as np
from napari._vispy.layers.base import VispyBaseLayer

from napari_plot._vispy.visuals.infline import InfLineVisual

if ty.TYPE_CHECKING:
    from napari_plot.layers import InfLine


class VispyInfLineLayer(VispyBaseLayer):
    """Infinite lines layer"""

    layer: "InfLine"
    node: InfLineVisual

    def __init__(self, layer: "InfLine"):
        node = InfLineVisual()
        super().__init__(layer, node)
        self.node.opacity = layer.opacity

        # connect events
        self.layer.events.color.connect(self._on_appearance_change)
        self.layer.events.highlight.connect(self._on_highlight_change)
        self.layer.events.width.connect(self._on_width_change)
        self.layer.events.adding.connect(self._on_adding_change)
        self.layer.events.removed.connect(self._on_remove_change)

        self.reset()
        self._on_data_change()

    def _on_adding_change(self, _event=None):
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
        """Remove lines."""
        to_remove = event.value
        for index in to_remove:
            self.node.remove(index)
        self.node.update()

    def _on_appearance_change(self, _event=None):
        """Change the appearance of the data"""
        pos, _orientation, color = self.layer._data_view.get_simple_lines_and_colors()
        selected = self.layer.selected_data
        for i in range(len(pos)):
            self.node._subvisuals[3 + i].set_data(
                pos=pos[i],
                color=self.layer._highlight_color if i in selected else color[i],
            )

    def _on_width_change(self, _event=None):
        """Change the appearance of the data"""
        for visual in self.node._subvisuals[3:]:
            visual.line_width = self.layer.width
        self.node.update()

    def _on_data_change(self, _event=None):
        """Set data"""
        pos, orientation, color = self.layer._data_view.get_simple_lines_and_colors()

        # add new visuals
        selected = self.layer.selected_data
        n_in_visual = len(self.node._subvisuals) - 3
        added = []
        if n_in_visual < len(pos):
            for i in range(n_in_visual, len(pos)):
                self.node.create(
                    pos[i],
                    color=self.layer._highlight_color if i in selected else color[i],
                    vertical=orientation[i] == 0,
                )
                added.append(i)

        # update position and color
        for i in range(len(pos)):
            # was just added so no need to update
            if i in added:
                continue
            self.node._subvisuals[3 + i].set_data(
                pos=pos[i],
                color=self.layer._highlight_color if i in selected else color[i],
            )
        self.node.update()

    def _on_highlight_change(self, _event=None):
        """Highlight."""
        # TODO: this is actually quite dumb since it will constantly update the highlight
        self._on_appearance_change()

        # Compute the location and properties of the vertices and box that
        # need to get rendered
        edge_color, pos, width = self.layer._compute_box()

        # add region edges
        if pos is None or len(pos) == 0:
            pos = np.zeros((1, self.layer._slice_input.ndisplay))
            width = 0
        self.node.select_box.set_data(pos=pos, color=edge_color, width=width)
        self.node.update()

    def close(self):
        """Vispy visual is closing."""
        self.node.remove_all()
        super().close()
