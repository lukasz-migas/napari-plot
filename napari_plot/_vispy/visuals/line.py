"""Scatter visual."""
from vispy.scene.visuals import Compound, Line, Markers


class LineVisual(Compound):
    """Compound vispy visual for line visualisation

    Components:
        - Line: for line plotting
        - Markers: for scatter points
    """

    def __init__(self):
        super().__init__([Line(), Markers()])
