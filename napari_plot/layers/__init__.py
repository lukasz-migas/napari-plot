"""Layers are the viewable objects that can be added to a viewer.

Custom layers must inherit from Layer and pass along the
`visual node <http://vispy.org/scene.html#module-vispy.scene.visuals>`_
to the super constructor.
"""
from napari.layers.points import Points  # noqa: F401
from napari.layers.shapes import Shapes  # noqa: F401

from .centroids import Centroids  # noqa: F401
from .infline import InfLine  # noqa: F401
from .line import Line  # noqa: F401
from .multiline import MultiLine  # noqa: F401
from .region import Region  # noqa: F401
from .scatter import Scatter  # noqa: F401
