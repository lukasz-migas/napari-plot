"""Zoom-box tool."""
import typing as ty
from enum import Enum

import numpy as np
from napari.layers.shapes._mesh import Mesh
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import EventedModel
from napari.utils.events.custom_types import Array
from pydantic import validator

from ..layers.region._region import Box, Horizontal, Vertical

if ty.TYPE_CHECKING:
    from napari.layers.shapes._shapes_models.rectangle import Rectangle


class Shape(str, Enum):
    """Orientation of the span"""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    BOX = "box"


span_classes = {Shape.HORIZONTAL: Horizontal, Shape.VERTICAL: Vertical, Shape.BOX: Box}


class BoxTool(EventedModel):
    """Zoom tool that is represented by rectangular box.

    visible : bool
        Controls the visibility of the box.
    color :
        Controls the color of the box.
    opacity : float
        Controls the opacity of the box.
    position : ty.Tuple[float, float, float, float]
        Position of the rectangular box specified as `x_min, x_max, y_min, y_max`.
    shape : Shape
        Controls the shape of the box. The box can take one of three possible shapes determined by the `shape` attribute
        HORIZONTAL : `infinite` horizontal box that spans between `y_min` and `y_max`. Can be used to zoom in on the
            y-axis.
        VERTICAL : `infinite` vertical box that spans between `x_min` and `x_max`. Can be used to zoom in on the x-axis.
        BOX : regular rectangular box that spans between `x_min` and `x_max` in the horizontal axis and `y_min` and
            `y_max` in the vertical axis.
    """

    visible: bool = False
    color: Array[float, (4,)] = (1.0, 1.0, 1.0, 1.0)
    opacity: float = 0.3
    position: ty.Tuple[float, float, float, float] = (0, 0, 0, 0)
    shape: Shape = Shape.VERTICAL

    # private attributes
    _mesh: Mesh = Mesh(ndisplay=2)

    @validator("color", pre=True)
    def _coerce_color(cls, v):
        return transform_color(v)[0]

    @property
    def mesh(self):
        """Retrieve Mesh. Each time the instance of Mesh is accessed, it is updated with most recent box positions."""
        if self.shape == Shape.VERTICAL:
            span = Vertical(self.position[0:2], z_index=0)
        elif self.shape == Shape.HORIZONTAL:
            span = Horizontal(self.position[2:], z_index=0)
        else:
            span = Box(self.position, edge_width=0, z_index=0)
        self._mesh.clear()
        self._add(span)
        return self._mesh

    def _add(self, span: "Rectangle"):
        # Add faces to mesh
        m = len(self._mesh.vertices)
        vertices = span._face_vertices
        self._mesh.vertices = np.append(self._mesh.vertices, vertices, axis=0)
        vertices = span._face_vertices
        self._mesh.vertices_centers = np.append(self._mesh.vertices_centers, vertices, axis=0)
        vertices = np.zeros(span._face_vertices.shape)
        self._mesh.vertices_offsets = np.append(self._mesh.vertices_offsets, vertices, axis=0)
        index = np.repeat([[0, 0]], len(vertices), axis=0)
        self._mesh.vertices_index = np.append(self._mesh.vertices_index, index, axis=0)

        triangles = span._face_triangles + m
        self._mesh.triangles = np.append(self._mesh.triangles, triangles, axis=0)
        index = np.repeat([[0, 0]], len(triangles), axis=0)
        self._mesh.triangles_index = np.append(self._mesh.triangles_index, index, axis=0)
        color_array = np.repeat([self.color], len(triangles), axis=0)
        self._mesh.triangles_colors = np.append(self._mesh.triangles_colors, color_array, axis=0)
