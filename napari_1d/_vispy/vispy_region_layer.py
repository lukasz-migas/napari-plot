"""Region layer"""
import numpy as np
from napari._vispy.vispy_base_layer import VispyBaseLayer
from vispy.scene.visuals import Compound, Line, Mesh

from ..layers import Region


class VispyRegionLayer(VispyBaseLayer):
    """Infinite region layer"""

    def __init__(self, layer: Region):
        # Create a compound visual with the following four sub-visuals:
        # Mesh: The actual meshes of the shape faces and edges
        # Mesh: The mesh of the outlines for each shape used for highlights
        # Lines: The lines of the interaction box used for highlights
        node = Compound([Mesh(), Mesh(), Line()])
        super().__init__(layer, node)

        self.layer.events.face_color.connect(self._on_data_change)
        self.layer.events.highlight.connect(self._on_highlight_change)

        self._reset_base()
        self._on_data_change()

    def _on_data_change(self, _event=None):
        """Set data"""
        faces = self.layer._data_view._mesh.displayed_triangles
        colors = self.layer._data_view._mesh.displayed_triangles_colors
        vertices = self.layer._data_view._mesh.vertices

        # Note that the indices of the vertices need to be reversed to
        # go from numpy style to xyz
        if vertices is not None:
            vertices = vertices[:, ::-1]

        if len(vertices) == 0 or len(faces) == 0:
            vertices = np.zeros((3, self.layer._ndisplay))
            faces = np.array([[0, 1, 2]])
            colors = np.array([[0, 0, 0, 0]])

        self.node._subvisuals[0].set_data(vertices=vertices, faces=faces, face_colors=colors)

        # Call to update order of translation values with new dims:
        self._on_matrix_change()
        self.node.update()

    def _on_highlight_change(self, event=None):
        """Highlight."""
        # Compute the vertices and faces of any shape outlines
        vertices, faces = self.layer._outline_shapes()
        if vertices is None or len(vertices) == 0 or len(faces) == 0:
            vertices = np.zeros((3, self.layer._ndisplay))
            faces = np.array([[0, 1, 2]])

        self.node._subvisuals[1].set_data(
            vertices=vertices,
            faces=faces,
            color=self.layer._highlight_color,
        )

        # Compute the location and properties of the vertices and box that
        # need to get rendered
        (
            _vertices,
            _face_color,
            edge_color,
            pos,
            _width,
        ) = self.layer._compute_vertices_and_box()

        # add region edges
        width = 3
        if pos is None or len(pos) == 0:
            pos = np.zeros((1, self.layer._ndisplay))
            width = 0
        self.node._subvisuals[2].set_data(pos=pos, color=edge_color, width=width)
