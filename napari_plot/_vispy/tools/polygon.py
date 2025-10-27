"""Span visual - based on the `Region` layer"""

from __future__ import annotations

import typing as ty

import numpy as np
from vispy.scene.visuals import Compound, LinearRegion, Markers, Mesh

from napari_plot.components.dragtool import POLYGON_TOOLS
from napari_plot.components.tools import BoxTool, PolygonTool, Shape

if ty.TYPE_CHECKING:
    from napari_plot.components.viewer_model import ViewerModel

MESH = 0
MARKERS = 1
HORIZONTAL_SPAN = 2
VERTICAL_SPAN = 3


class VispyPolygonVisual:
    """Box visual user to select region of interest in 1d."""

    def __init__(self, viewer: ViewerModel, parent=None, order=1e6):
        self._viewer = viewer

        self.node = Compound(
            [
                Mesh(),
                Markers(),
                LinearRegion(
                    pos=[0, 0],
                    color=[0.0, 1.0, 0.0, 0.5],
                    vertical=False,
                ),
                LinearRegion(
                    pos=[0, 0],
                    color=[0.0, 1.0, 0.0, 0.5],
                    vertical=True,
                ),
            ]
        )
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

    @property
    def tool(self) -> BoxTool | PolygonTool:
        """Return current tool."""
        return self._viewer.drag_tool.tool

    @property
    def shape(self) -> Shape | None:
        """Shape of the span"""
        if hasattr(self.tool, "shape"):
            return self.tool.shape
        return None

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
        shape = self.shape

        # Handle standard rectangle box
        if shape is None or shape == Shape.BOX:
            faces = self.tool.mesh.triangles
            colors = self.tool.mesh.triangles_colors
            vertices = self.tool.mesh.vertices
            if vertices is not None:
                vertices = vertices[:, ::-1]
            if len(vertices) == 0 or len(faces) == 0:
                vertices = np.zeros((3, 2))
                faces = np.array([[0, 1, 2]])
                colors = np.array([[0, 0, 0, 0]])
            self.node._subvisuals[MESH].set_data(vertices=vertices, faces=faces, face_colors=colors)
            self.node._subvisuals[VERTICAL_SPAN].set_data(pos=[0, 0])
            self.node._subvisuals[HORIZONTAL_SPAN].set_data(pos=[0, 0])
        # handle vertical span
        elif shape == Shape.VERTICAL:
            self.node._subvisuals[MESH].set_data(
                vertices=np.zeros((3, 2)),
                faces=np.array([[0, 1, 2]]),
                face_colors=np.array([[0, 0, 0, 0]]),
            )
            self.node._subvisuals[VERTICAL_SPAN].set_data(pos=self.tool.vertical, color=self.tool.color)
            self.node._subvisuals[HORIZONTAL_SPAN].set_data(pos=[0, 0])
        # handle horizontal span
        elif shape == Shape.HORIZONTAL:
            self.node._subvisuals[MESH].set_data(
                vertices=np.zeros((3, 2)),
                faces=np.array([[0, 1, 2]]),
                face_colors=np.array([[0, 0, 0, 0]]),
            )
            self.node._subvisuals[HORIZONTAL_SPAN].set_data(pos=self.tool.horizontal, color=self.tool.color)
            self.node._subvisuals[VERTICAL_SPAN].set_data(pos=[0, 0])

        # Note that the indices of the vertices need to be reversed to
        # go from numpy style to xyz
        data = self.tool.data
        if data is not None:
            data = data[:, ::-1]
        self.node._subvisuals[MARKERS].set_data(data)
