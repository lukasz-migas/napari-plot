"""Scatter visual."""
from vispy.scene.visuals import Compound, Markers, Text


class ScatterVisual(Compound):
    """Compound vispy visual for scatter visualisation

    Components:
        - Markers: for scatter points
        - Markers: for scatter highlights
        - Text: Labels
    """

    def __init__(self):
        super().__init__([Markers(), Markers(), Text()])
