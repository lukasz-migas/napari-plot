"""Scatter visual."""
from __future__ import annotations

from napari._vispy.visuals.markers import Markers
from vispy.scene.visuals import Compound, Line, Text


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
    def points_markers(self) -> Markers:
        """Points markers visual"""
        return self._subvisuals[0]

    @property
    def selection_markers(self) -> Markers:
        """Highlight markers visual"""
        return self._subvisuals[1]

    @property
    def highlight_lines(self) -> Line:
        """Highlight lines visual"""
        return self._subvisuals[2]

    @property
    def text(self) -> Text:
        """Text labels visual"""
        return self._subvisuals[3]

    @property
    def symbol(self):
        """Symbol property for the markers visuals"""
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
        return self.points_markers.scaling == "visual"

    @scaling.setter
    def scaling(self, value):
        scaling_txt = "visual" if value else "fixed"
        self.points_markers.scaling = scaling_txt
        self.selection_markers.scaling = scaling_txt

    @property
    def antialias(self) -> float:
        return self.points_markers.antialias

    @antialias.setter
    def antialias(self, value: float) -> None:
        self.points_markers.antialias = value
        self.selection_markers.antialias = value

    @property
    def spherical(self) -> bool:
        return self.points_markers.spherical

    @spherical.setter
    def spherical(self, value: bool) -> None:
        self.points_markers.spherical = value

    @property
    def canvas_size_limits(self) -> tuple[int, int]:
        return self.points_markers.canvas_size_limits

    @canvas_size_limits.setter
    def canvas_size_limits(self, value: tuple[int, int]) -> None:
        self.points_markers.canvas_size_limits = value
        self.selection_markers.canvas_size_limits = value
