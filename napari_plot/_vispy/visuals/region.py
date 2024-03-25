"""Scatter visual."""

from vispy.scene.visuals import Compound, Line, Mesh


class RegionVisual(Compound):
    """Compound vispy visual for region visualisation

    Components:
        - Mesh: The actual meshes of the shape faces and edges
        - Mesh: The mesh of the outlines for each shape used for highlights
        - Lines: The lines of the interaction box used for highlights
    """

    def __init__(self):
        super().__init__([Mesh(), Mesh(), Line()])
