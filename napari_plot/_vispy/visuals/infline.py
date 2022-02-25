"""Scatter visual."""
from vispy.scene.visuals import Compound, Line


class InfLineVisual(Compound):
    """Compound vispy visual for infinite line visualisation

    Components:
        - Line: The actual infinite lines
        - Line: Used to draw selection box in the canvas.
        - Line: Highlight of the selected infinite line using different color and width
    """

    def __init__(self):
        super().__init__([Line(), Line(), Line()])
