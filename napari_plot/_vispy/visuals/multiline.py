"""Scatter visual."""

from vispy.scene.visuals import Compound, Line


class MultiLineVisual(Compound):
    """Compound vispy visual for multi-line visualisation

    Components:
        - Line: The actual line for displaying data
        - Line: The line used for selecting lines
        - Line: The lines of the interaction box used for highlights
    """

    def __init__(self):
        super().__init__([Line(), Line(), Line()])
