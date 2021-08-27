"""Span visual - based on the `Region` layer"""
from typing import TYPE_CHECKING

import numpy as np
from vispy.scene.visuals import Mesh

if TYPE_CHECKING:
    from ..components.viewer_model import ViewerModel


class VispyBoxVisual:
    """Box visual user to select region of interest in 1d."""

    def __init__(self, viewer: "ViewerModel", parent=None, order=1e6):
        self._viewer = viewer

        self.node = Mesh()
        self.node.order = order
        if parent:
            parent.add(self.node)

        self._viewer.box_tool.events.visible.connect(self._on_visible_change)
        self._viewer.box_tool.events.opacity.connect(self._on_opacity_change)
        self._viewer.box_tool.events.color.connect(self._on_data_change)
        self._viewer.box_tool.events.position.connect(self._on_data_change)

        self._on_visible_change()
        self._on_opacity_change()
        self._on_data_change()

    def _on_visible_change(self, _evt=None):
        """Change span visibility"""
        self.node.visible = self._viewer.box_tool.visible

    def _on_opacity_change(self, _evt=None):
        """Change span visibility"""
        self.node.opacity = self._viewer.box_tool.opacity

    def _on_data_change(self, _event=None):
        """Set data"""
        faces = self._viewer.box_tool.mesh.triangles
        colors = self._viewer.box_tool.mesh.triangles_colors
        vertices = self._viewer.box_tool.mesh.vertices

        # Note that the indices of the vertices need to be reversed to
        # go from numpy style to xyz
        if vertices is not None:
            vertices = vertices[:, ::-1]

        if len(vertices) == 0 or len(faces) == 0:
            vertices = np.zeros((3, 2))
            faces = np.array([[0, 1, 2]])
            colors = np.array([[0, 0, 0, 0]])
        self.node.set_data(vertices=vertices, faces=faces, face_colors=colors)
        self.node.update()
