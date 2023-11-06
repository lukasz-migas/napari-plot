"""Span visual - based on the `Region` layer"""
import typing as ty

import numpy as np
from vispy.scene.visuals import Compound, Markers, Mesh

from napari_plot.components.dragtool import POLYGON_TOOLS
from napari_plot.components.tools import BoxTool, PolygonTool

if ty.TYPE_CHECKING:
    from napari_plot.components.viewer_model import ViewerModel

MESH = 0
MARKERS = 1


class VispyPolygonVisual:
    """Box visual user to select region of interest in 1d."""

    def __init__(self, viewer: "ViewerModel", parent=None, order=1e6):
        self._viewer = viewer

        self.node = Compound([Mesh(), Markers()])
        self.node.order = order
        if parent:
            parent.add(self.node)

        self._viewer.drag_tool.events.tool.connect(self._on_tool_change)
        # polygon events
        self._viewer.drag_tool._polygon.events.visible.connect(self._on_visible_change)
        self._viewer.drag_tool._polygon.events.opacity.connect(self._on_opacity_change)
        self._viewer.drag_tool._polygon.events.color.connect(self._on_data_change)
        self._viewer.drag_tool._polygon.events.data.connect(self._on_data_change)
        self._viewer.drag_tool._polygon.events.finished.connect(self._on_data_finished_change)
        # box events
        self._viewer.drag_tool._box.events.visible.connect(self._on_visible_change)
        self._viewer.drag_tool._box.events.opacity.connect(self._on_opacity_change)
        self._viewer.drag_tool._box.events.color.connect(self._on_data_change)
        self._viewer.drag_tool._box.events.position.connect(self._on_data_finished_change)

        self._on_tool_change(None)

    def _on_tool_change(self, _evt=None):
        # only trigger an update if the tool is a polygon or boxtool
        if (
            self._viewer.drag_tool.active not in POLYGON_TOOLS or type(self._viewer.drag_tool.tool) != PolygonTool
        ) and type(self._viewer.drag_tool.tool) != BoxTool:
            return

        self._on_visible_change()
        self._on_opacity_change()
        self._on_data_change()

    def _on_visible_change(self, _evt=None):
        """Change span visibility"""
        self.node.visible = self._viewer.drag_tool.tool.visible

    def _on_opacity_change(self, _evt=None):
        """Change span visibility"""
        self.node.opacity = self._viewer.drag_tool.tool.opacity

    def _on_data_change(self, _event=None):
        """Set data"""
        data = self._viewer.drag_tool.tool.data

        # Note that the indices of the vertices need to be reversed to
        # go from numpy style to xyz
        if data is not None:
            data = data[:, ::-1]

        self.node._subvisuals[MARKERS].set_data(data)

    def _on_data_finished_change(self, _event=None):
        data = self._viewer.drag_tool.tool.data
        faces = self._viewer.drag_tool.tool.mesh.triangles
        colors = self._viewer.drag_tool.tool.mesh.triangles_colors
        vertices = self._viewer.drag_tool.tool.mesh.vertices

        # Note that the indices of the vertices need to be reversed to
        # go from numpy style to xyz
        if data is not None:
            data = data[:, ::-1]
        if vertices is not None:
            vertices = vertices[:, ::-1]

        if len(vertices) == 0 or len(faces) == 0:
            vertices = np.zeros((3, 2))
            faces = np.array([[0, 1, 2]])
            colors = np.array([[0, 0, 0, 0]])
        self.node._subvisuals[MARKERS].set_data(data)
        self.node._subvisuals[MESH].set_data(vertices=vertices, faces=faces, face_colors=colors)
