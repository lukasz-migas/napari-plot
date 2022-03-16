"""Zoom-box tool."""
import typing as ty
from enum import Enum

import numpy as np
from napari.layers.shapes._mesh import Mesh
from napari.layers.shapes._shapes_models import Path, Polygon, Rectangle
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import EventedModel
from napari.utils.events.custom_types import Array
from pydantic import validator

from ..layers.region._region import Box, Horizontal, Vertical


class Shape(str, Enum):
    """Orientation of the span"""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    BOX = "box"


span_classes = {Shape.HORIZONTAL: Horizontal, Shape.VERTICAL: Vertical, Shape.BOX: Box}


class BaseTool(EventedModel):
    """Base class for all drag tools."""

    visible: bool = False
    color: Array[float, (4,)] = (0.0, 0.0, 1.0, 1.0)
    opacity: float = 0.5


class MeshBaseTool(BaseTool):
    """Mesh-based tool."""

    position: Array[float, (4,)] = (0.0, 0.0, 0.0, 0.0)

    # private attributes
    _mesh: Mesh = Mesh(ndisplay=2)

    @validator("position", pre=True)
    def _validate_position(cls, v):
        assert len(v) == 4, "Incorrect number of elements passed to the BoxTool position value."
        x0, x1, y0, y1 = v
        x0, x1 = (x0, x1) if x0 < x1 else (x1, x0)
        y0, y1 = (y0, y1) if y0 < y1 else (y1, y0)
        return np.asarray([x0, x1, y0, y1])

    @property
    def mesh(self):
        """Retrieve Mesh. Each time the instance of Mesh is accessed, it is updated with most recent box positions."""
        raise NotImplementedError("Must implement method")

    def _add(self, box: ty.Union[Path, Polygon, Rectangle]):
        # Add faces to mesh
        m = len(self._mesh.vertices)
        vertices = box._face_vertices
        self._mesh.vertices = np.append(self._mesh.vertices, vertices, axis=0)
        vertices = box._face_vertices
        self._mesh.vertices_centers = np.append(self._mesh.vertices_centers, vertices, axis=0)
        vertices = np.zeros(box._face_vertices.shape)
        self._mesh.vertices_offsets = np.append(self._mesh.vertices_offsets, vertices, axis=0)
        index = np.repeat([[0, 0]], len(vertices), axis=0)
        self._mesh.vertices_index = np.append(self._mesh.vertices_index, index, axis=0)

        triangles = box._face_triangles + m
        self._mesh.triangles = np.append(self._mesh.triangles, triangles, axis=0)
        index = np.repeat([[0, 0]], len(triangles), axis=0)
        self._mesh.triangles_index = np.append(self._mesh.triangles_index, index, axis=0)
        color_array = np.repeat([self.color], len(triangles), axis=0)
        self._mesh.triangles_colors = np.append(self._mesh.triangles_colors, color_array, axis=0)


class BoxTool(MeshBaseTool):
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

    shape: Shape = Shape.VERTICAL

    @property
    def data(self):
        """Get vertices data."""
        x0, x1, y0, y1 = self.position
        return np.asarray([[y0, x0], [y1, x0], [y1, x1], [y0, x1]])

    @validator("color", pre=True)
    def _coerce_color(cls, v):
        return transform_color(v)[0]

    @property
    def mesh(self):
        """Retrieve Mesh. Each time the instance of Mesh is accessed, it is updated with most recent box positions."""
        if self.shape == Shape.VERTICAL:
            box = Vertical(self.position[0:2])
        elif self.shape == Shape.HORIZONTAL:
            box = Horizontal(self.position[2:])
        else:
            box = Box(self.position, edge_width=0)
        self._mesh.clear()
        self._add(box)
        return self._mesh


class PolygonTool(MeshBaseTool):
    """Class for polygon and lasso tool."""

    data: Array[float, (-1, 2)] = np.zeros((0, 2), dtype=float)
    auto_reset: bool = False

    @validator("data", pre=True)
    def _validate_position(cls, v):
        v = np.asarray(v)
        assert v.ndim == 2
        return v

    @property
    def mesh(self):
        """Retrieve Mesh. Each time the instance of Mesh is accessed, it is updated with most recent box positions."""
        self._mesh.clear()
        if len(self.data) >= 2:
            if len(self.data) < 2:
                poly = Path(self.data, edge_width=0)
            else:
                poly = Polygon(self.data, edge_width=0)
            self._add(poly)
        return self._mesh

    def add_point(self, point: ty.Tuple[float, float]):
        """Add point to the polygon."""
        if len(self.data) > 0:
            if np.all(self.data[-1] == point):
                return
        self.data = np.vstack((self.data, point))

    def remove_point(self, index: int):
        """Remove point from the polygon."""
        if len(self.data) == 0:
            return
        data = np.delete(self.data, index, axis=0)
        self.data = data

    def remove_nearby_point(self, point: ty.Tuple[float, float]):
        """Remove point that is nearby to the specified point."""
        from scipy.spatial.distance import cdist

        if len(self.data) == 0:
            return
        index = cdist(self.data, [point])
        index = index.argmin()
        self.remove_point(index)

    def clear(self):
        """Clear all data."""
        self.data = np.zeros((0, 2), dtype=float)
