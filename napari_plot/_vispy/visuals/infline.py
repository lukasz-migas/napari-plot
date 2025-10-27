"""Scatter visual."""

import numpy as np
from vispy.scene.visuals import Compound, InfiniteLine, Line

LINE_BOX = 0
HORIZONTAL_INFLINE = 1
VERTICAL_INFLINE = 2


class InfLineVisual(Compound):
    """Compound vispy visual for infinite line visualisation

    Components:
        - Line: Highlight of the selected infinite line using different color and width
        - InfiniteLine: Horizontal line used for drawing temporary lines.
        - InfiniteLine: Vertical line used for drawing temporary lines.
    """

    _opacity: float

    def __init__(self):
        super().__init__(
            [
                Line(),
                InfiniteLine(vertical=False),
                InfiniteLine(vertical=True),
            ]
        )

    @property
    def select_box(self) -> Line:
        """Selection box visual"""
        return self._subvisuals[LINE_BOX]

    @property
    def horizontal_visual(self) -> InfiniteLine:
        """Horizontal infinite line visual"""
        return self._subvisuals[HORIZONTAL_INFLINE]

    @property
    def vertical_visual(self) -> InfiniteLine:
        """Vertical infinite line visual"""
        return self._subvisuals[VERTICAL_INFLINE]

    def create(self, pos: float, vertical: bool, color: np.ndarray) -> None:
        """Create new visuals"""
        visual = InfiniteLine(pos, color=color, vertical=vertical, parent=self.parent)
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
