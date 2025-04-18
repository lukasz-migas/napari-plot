"""Region layer"""

import typing as ty

import numpy as np
from napari._vispy.layers.base import VispyBaseLayer
from vispy.scene.visuals import Compound, Line, LinearRegion

if ty.TYPE_CHECKING:
    from napari_plot.layers import Region

LINE_BOX = 0
HORIZONTAL_SPAN = 1
VERTICAL_SPAN = 2


class RegionVisual(Compound):
    """Compound vispy visual for region visualisation

    Components:
        - Lines: The lines of the interaction box used for highlights
        - Mesh: The actual meshes of the shape faces and edges
        - Mesh: The mesh of the outlines for each shape used for highlights
    """

    def __init__(self):
        super().__init__([Line(), LinearRegion([0, 0], vertical=False), LinearRegion([0, 0], vertical=True)])


class VispyRegionLayer(VispyBaseLayer):
    """Infinite region layer"""

    layer: "Region"
    node: RegionVisual

    def __init__(self, layer: "Region"):
        node = RegionVisual()
        super().__init__(layer, node)

        self.layer.events.color.connect(self._on_data_change)
        self.layer.events.highlight.connect(self._on_highlight_change)

        self.reset()
        self._on_data_change()

    def _on_data_change(self, _event=None):
        """Set data"""
        orientation = self.layer.orientation
        data = self.layer.data
        # n_in_visual = len(self.node._subvisuals) - 3

        # need to add new visual
        # if n_in_visual != len(data):
        for orientation_, data_ in zip(orientation, data):
            if orientation_ == "horizontal":
                min_val, max_val = data_[0, 0], data_[2, 0]
            else:
                min_val, max_val = data_[0, 1], data_[2, 1]
            min_val, max_val = min(min_val, min_val), max(max_val, max_val)
            if orientation_ == "horizontal":
                self.node._subvisuals[VERTICAL_SPAN].set_data(pos=[min_val, max_val])
            else:
                self.node._subvisuals[VERTICAL_SPAN].set_data(pos=[min_val, max_val])

        # faces = self.layer._data_view._mesh.displayed_triangles
        # colors = self.layer._data_view._mesh.displayed_triangles_colors
        # vertices = self.layer._data_view._mesh.vertices
        #
        # # Note that the indices of the vertices need to be reversed to go from numpy style to xyz
        # if vertices is not None:
        #     vertices = vertices[:, ::-1]
        #
        # if len(vertices) == 0 or len(faces) == 0:
        #     vertices = np.zeros((3, self.layer._slice_input.ndisplay))
        #     faces = np.array([[0, 1, 2]])
        #     colors = np.array([[0, 0, 0, 0]])
        #
        # self.node._subvisuals[MESH_MAIN].set_data(vertices=vertices, faces=faces, face_colors=colors)
        # self.node._subvisuals[MESH_HIGHLIGHT].set_data(vertices=vertices, faces=faces, face_colors=colors)

        # Call to update order of translation values with new dims:
        self._on_matrix_change()
        self.node.update()

    def _on_highlight_change(self, event=None):
        """Highlight."""
        # Compute the vertices and faces of selected regions
        # vertices, faces = self.layer._highlight_regions()
        # if vertices is None or len(vertices) == 0 or len(faces) == 0:
        #     vertices = np.zeros((3, self.layer._slice_input.ndisplay))
        #     faces = np.array([[0, 1, 2]])
        # self.node._subvisuals[MESH_HIGHLIGHT].set_data(
        #     vertices=vertices,
        #     faces=faces,
        #     color=self.layer._highlight_color,
        # )

        # Compute the location and properties of the vertices and box that
        # need to get rendered
        edge_color, pos = self.layer._compute_vertices_and_box()

        # add region edges
        width = 3  # set
        if pos is None or len(pos) == 0:
            pos = np.zeros((1, self.layer._slice_input.ndisplay))
            width = 0
        self.node._subvisuals[LINE_BOX].set_data(pos=pos, color=edge_color, width=width)
