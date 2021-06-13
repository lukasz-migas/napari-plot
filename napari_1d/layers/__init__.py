"""Layers are the viewable objects that can be added to a viewer.

Custom layers must inherit from Layer and pass along the
`visual node <http://vispy.org/scene.html#module-vispy.scene.visuals>`_
to the super constructor.
"""
from napari.layers.points import Points  # noqa
from napari.layers.shapes import Shapes  # noqa
from .centroids import Centroids
from .infline import InfLine
from .line import Line
from .region import Region
from .scatter import Scatter
