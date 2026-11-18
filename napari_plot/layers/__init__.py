"""Layers are the viewable objects that can be added to a viewer.

Custom layers must inherit from Layer and pass along the
`visual node <http://vispy.org/scene.html#module-vispy.scene.visuals>`_
to the super constructor.
"""

from typing import NewType

from napari import layers as _napari_layers, types as _napari_types
from napari.layers.image import Image
from napari.layers.points import Points
from napari.layers.shapes import Shapes
from napari.layers.vectors import Vectors

from napari_plot.layers.areas import Areas
from napari_plot.layers.band import Band
from napari_plot.layers.bar import Bar
from napari_plot.layers.centroids import Centroids
from napari_plot.layers.error_bar import ErrorBar
from napari_plot.layers.infline import InfLine
from napari_plot.layers.line import Line
from napari_plot.layers.multiline import MultiLine
from napari_plot.layers.rectangles import Rectangles
from napari_plot.layers.region import Region
from napari_plot.layers.scatter import Scatter
from napari_plot.layers.text import Text


def _register_custom_layer_types() -> None:
    """Register custom layers and their data types with napari."""
    for layer_type in (Areas, Band, Bar, Centroids, ErrorBar, InfLine, Line, MultiLine, Rectangles, Region, Scatter, Text):
        type_name = layer_type.__name__.lower()
        data_type_name = f"{type_name.title()}Data"
        _napari_layers.NAMES.add(type_name)
        setattr(_napari_layers, type_name.title(), layer_type)
        setattr(
            _napari_types,
            data_type_name,
            NewType(data_type_name, object),
        )


_register_custom_layer_types()

__all__ = [
    "Areas",
    "Band",
    "Bar",
    "Centroids",
    "ErrorBar",
    "Image",
    "InfLine",
    "Line",
    "MultiLine",
    "Points",
    "Rectangles",
    "Region",
    "Scatter",
    "Shapes",
    "Text",
    "Vectors",
]
