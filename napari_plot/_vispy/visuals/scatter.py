"""Scatter visual."""
from vispy.scene.visuals import Compound, Line, Markers, Text


class ScatterVisual(Compound):
    """Compound vispy visual for scatter visualisation

    Components:
        - Markers: for scatter points
        - Markers: for scatter highlights
        - Line: for highlights
        - Text: Labels
    """

    def __init__(self):
        super().__init__([Markers(), Markers(), Line(), Text()])

    @property
    def symbol(self):
        return self._subvisuals[0].symbol

    @symbol.setter
    def symbol(self, value):
        for marker in self._subvisuals[:2]:
            marker.symbol = value

    @property
    def scaling(self):
        """
        Scaling property for both the markers visuals. If set to true,
        the points rescale based on zoom (i.e: constant world-space size)
        """
        return self._subvisuals[0].scaling

    @scaling.setter
    def scaling(self, value):
        for marker in self._subvisuals[:2]:
            marker.scaling = value

    @property
    def antialias(self):
        return self._subvisuals[0].antialias

    @antialias.setter
    def antialias(self, value):
        for marker in self._subvisuals[:2]:
            marker.antialias = value

    @property
    def spherical(self):
        return self._subvisuals[0].spherical

    @spherical.setter
    def spherical(self, value):
        self._subvisuals[0].spherical = value

    @property
    def canvas_size_limits(self):
        return self._subvisuals[0].canvas_size_limits

    @canvas_size_limits.setter
    def canvas_size_limits(self, value):
        self._subvisuals[0].canvas_size_limits = value
