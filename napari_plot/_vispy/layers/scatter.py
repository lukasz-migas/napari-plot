"""Scatter points layer"""
import typing as ty

import numpy as np
from napari._vispy.layers.base import VispyBaseLayer
from napari._vispy.utils.gl import BLENDING_MODES
from napari._vispy.utils.text import update_text
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import disconnect_events

from ..visuals.scatter import ScatterVisual

if ty.TYPE_CHECKING:
    from ...layers import Scatter


MARKERS_MAIN = 0
MARKERS_HIGHLIGHT = 1
RECT_HIGHLIGHT = 2
TEXT = 3


class VispyScatterLayer(VispyBaseLayer):
    """Line layer"""

    _highlight_color = (0, 0.6, 1)
    _highlight_width = 3

    def __init__(self, layer: "Scatter"):
        node = ScatterVisual()
        super().__init__(layer, node)

        self.layer.events.symbol.connect(self._on_symbol_change)
        self.layer.events.scaling.connect(self._on_scaling_change)
        self.layer.events.symbol.connect(self._on_data_change)
        self.layer.events.edge_width.connect(self._on_data_change)
        self.layer.events.edge_width_is_relative.connect(self._on_data_change)
        self.layer.events.edge_color.connect(self._on_data_change)
        self.layer._edge.events.colors.connect(self._on_data_change)
        self.layer._edge.events.color_properties.connect(self._on_data_change)
        self.layer.events.face_color.connect(self._on_data_change)
        self.layer._face.events.colors.connect(self._on_data_change)
        self.layer._face.events.color_properties.connect(self._on_data_change)
        self.layer.events.highlight.connect(self._on_highlight_change)
        self.layer.text.events.connect(self._on_text_change)
        # self.layer.events.shading.connect(self._on_shading_change)
        # self.layer.events.antialiasing.connect(self._on_antialiasing_change)
        # self.layer.events.canvas_size_limits.connect(
        #     self._on_canvas_size_limits_change
        # )

        self.reset()
        self._on_data_change()

    def _on_scaling_change(self, event=None):
        """Set data"""
        self.node.scaling = self.layer.scaling

    def _on_antialiasing_change(self):
        self.node.antialias = self.layer.antialiasing

    def _on_shading_change(self):
        shading = self.layer.shading
        if shading == "spherical":
            self.node.spherical = True
        else:
            self.node.spherical = False

    def _on_canvas_size_limits_change(self):
        self.node.canvas_size_limits = self.layer.canvas_size_limits

    def _on_symbol_change(self, event=None):
        """Set data"""
        self.node._subvisuals[MARKERS_MAIN].symbol = self.layer.symbol
        self.node._subvisuals[MARKERS_MAIN].symbol = self.layer.symbol

    def _on_data_change(self):
        if len(self.layer._indices_view) > 0:
            edge_color = self.layer._view_edge_color
            face_color = self.layer._view_face_color
        else:
            edge_color = np.array([[0.0, 0.0, 0.0, 1.0]], dtype=np.float32)
            face_color = np.array([[1.0, 1.0, 1.0, 1.0]], dtype=np.float32)

            # Set vispy data, noting that the order of the points needs to be
            # reversed to make the most recently added point appear on top
            # and the rows / columns need to be switched for vispy's x / y ordering
        if len(self.layer._indices_view) == 0:
            data = np.zeros((1, self.layer._ndisplay))
            size = [0]
            edge_width = [0]
        else:
            data = self.layer._view_data
            size = self.layer._view_size
            edge_width = self.layer._view_edge_width

        # # Set vispy data, noting that the order of the points needs to be
        # # reversed to make the most recently added point appear on top
        # # and the rows / columns need to be switched for vispy's x / y ordering
        # if len(self.layer._indices_view) == 0:
        #     # always pass one invisible point to avoid issues
        #     data = np.zeros((1, self.layer._ndisplay))
        #     size = [0]
        #     edge_color = np.array([[0.0, 0.0, 0.0, 1.0]], dtype=np.float32)
        #     face_color = np.array([[1.0, 1.0, 1.0, 1.0]], dtype=np.float32)
        #     edge_width = [0]
        #     symbol = ["o"]
        # else:
        #     data = self.layer._view_data
        #     size = self.layer._view_size
        #     edge_color = self.layer._view_edge_color
        #     face_color = self.layer._view_face_color
        #     edge_width = self.layer._view_edge_width
        #     symbol = self.layer._view_symbol

        set_data = self.node._subvisuals[MARKERS_MAIN].set_data

        if self.layer.edge_width_is_relative:
            edge_kw = {
                "edge_width": None,
                "edge_width_rel": edge_width,
            }
        else:
            edge_kw = {
                "edge_width": edge_width,
                "edge_width_rel": None,
            }

        set_data(
            data[:, ::-1],
            size=size,
            # symbol=symbol,
            edge_color=edge_color,
            face_color=face_color,
            **edge_kw,
        )

        self.reset()

    def _on_symbol_change(self):
        self.node.symbol = self.layer.symbol

    def _on_highlight_change(self):
        if len(self.layer._highlight_index) > 0:
            # Color the hovered or selected points
            data = self.layer._view_data[self.layer._highlight_index]
            if data.ndim == 1:
                data = np.expand_dims(data, axis=0)
            size = self.layer._view_size[self.layer._highlight_index]
            # symbol = self.layer._view_symbol[self.layer._highlight_index]
        else:
            data = np.zeros((1, self.layer._ndisplay))
            size = 0
            # symbol = ["o"]

        self.node._subvisuals[MARKERS_HIGHLIGHT].set_data(
            data[:, ::-1],
            size=size,
            # symbol=symbol,
            edge_width=self._highlight_width,
            edge_color=self._highlight_color,
            face_color=transform_color("transparent"),
        )

        if self.layer._highlight_box is None or 0 in self.layer._highlight_box.shape:
            pos = np.zeros((1, self.layer._ndisplay))
            width = 0
        else:
            pos = self.layer._highlight_box
            width = self._highlight_width

        self.node._subvisuals[RECT_HIGHLIGHT].set_data(
            pos=pos[:, ::-1],
            color=self._highlight_color,
            width=width,
        )

        self.node.update()

    def _update_text(self, *, update_node=True):
        """Function to update the text node properties

        Parameters
        ----------
        update_node : bool
            If true, update the node after setting the properties
        """
        update_text(node=self.node._subvisuals[TEXT], layer=self.layer)
        if update_node:
            self.node.update()

    def _on_text_change(self, event=None):
        if event is not None:
            if event.type == "blending":
                self._on_blending_change(event)
                return
            if event.type == "values":
                return
        self._update_text()

    def _on_blending_change(self):
        """Function to set the blending mode"""
        points_blending_kwargs = BLENDING_MODES[self.layer.blending]
        self.node.set_gl_state(**points_blending_kwargs)

        text_node = self.node._subvisuals[TEXT]
        text_blending_kwargs = BLENDING_MODES[self.layer.text.blending]
        text_node.set_gl_state(**text_blending_kwargs)

        # selection box is always without depth
        box_blending_kwargs = BLENDING_MODES["translucent_no_depth"]
        self.node._subvisuals[RECT_HIGHLIGHT].set_gl_state(**box_blending_kwargs)

        self.node.update()

    def reset(self):
        super().reset()
        self._update_text(update_node=False)
        self._on_highlight_change()
        # self._on_antialiasing_change()
        # self._on_shading_change()
        # self._on_canvas_size_limits_change()

    def close(self):
        """Vispy visual is closing."""
        disconnect_events(self.layer.text.events, self)
        super().close()
