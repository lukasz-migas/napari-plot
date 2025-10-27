"""Scatter visual."""

from __future__ import annotations

import numpy as np
from vispy.scene.visuals import Compound, Line, LinearRegion

LINE_BOX = 0
HORIZONTAL_REGION = 1
VERTICAL_REGION = 2


class RegionVisual(Compound):
    """Compound vispy visual for region visualisation

    Components:
        - Line: Highlight of the selected infinite line using different color and width
        - LinearRegion: Horizontal line used for drawing temporary regions.
        - LinearRegion: Vertical line used for drawing temporary regions.
    """

    _opacity: float

    def __init__(self):
        super().__init__(
            [
                Line(),
                LinearRegion([0, 0], [0, 0, 0, 0], vertical=False),
                LinearRegion([0, 0], [0, 0, 0, 0], vertical=True),
            ]
        )

    @property
    def select_box(self) -> Line:
        """Selection box visual"""
        return self._subvisuals[LINE_BOX]

    @property
    def horizontal_visual(self) -> LinearRegion:
        """Horizontal infinite line visual"""
        return self._subvisuals[HORIZONTAL_REGION]

    @property
    def vertical_visual(self) -> LinearRegion:
        """Vertical infinite line visual"""
        return self._subvisuals[VERTICAL_REGION]

    def create(
        self, pos: tuple[float, float], vertical: bool, color: np.ndarray
    ) -> None:
        """Create new visuals"""
        visual = LinearRegion(pos, color=color, vertical=vertical, parent=self.parent)
        visual.opacity = self._opacity
        self.add_subvisual(visual)
        visual.transform = self._subvisuals[0].transform

    def remove(self, index: int) -> None:
        """Remove visual."""
        visual = self._subvisuals[3 + index]
        visual.parent = None
        self.remove_subvisual(visual)

    def remove_all(self) -> None:
        """Remove all lines"""
        for visual in self._subvisuals[3:]:
            visual.parent = None
            self.remove_subvisual(visual)

    @property
    def opacity(self):
        """Opacity."""
        return self._opacity

    @opacity.setter
    def opacity(self, o):
        """Opacity."""
        self._opacity = o
        for visual in self._subvisuals[3:]:
            visual.opacity = o
        self.select_box.opacity = 1.0
        self._update_opacity()
        self.update()

    @property
    def visible(self):
        """Visible."""
        return self._vshare.visible

    @visible.setter
    def visible(self, v):
        if v != self._vshare.visible:
            self._vshare.visible = v
            for visual in self._subvisuals[3:]:
                visual.visible = v
            self.update()
