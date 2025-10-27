"""Layers are the viewable objects that can be added to a viewer.

Custom layers must inherit from Layer and pass along the
`visual node <http://vispy.org/scene.html#module-vispy.scene.visuals>`_
to the super constructor.
"""

from napari.layers.image import Image
from napari.layers.points import Points
from napari.layers.shapes import Shapes

from napari_plot.layers.centroids import Centroids
from napari_plot.layers.infline import InfLine
from napari_plot.layers.line import Line
from napari_plot.layers.multiline import MultiLine
from napari_plot.layers.region import Region
from napari_plot.layers.scatter import Scatter

__all__ = [
    "Centroids",
    "Image",
    "InfLine",
    "Line",
    "MultiLine",
    "Points",
    "Region",
    "Scatter",
    "Shapes",
]
