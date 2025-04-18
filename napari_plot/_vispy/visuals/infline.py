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
        - InfiniteLine: The actual infinite lines
        - InfiniteLine: Used to draw selection box in the canvas.
    """

    _opacity: float

    def __init__(self):
        super().__init__([Line(), InfiniteLine(vertical=False), InfiniteLine(vertical=True)])

    @property
    def select_box(self) -> Line:
        """Selection box visual"""
        return self._subvisuals[LINE_BOX]

    @property
    def horizontal_infline(self) -> InfiniteLine:
        """Horizontal infinite line visual"""
        return self._subvisuals[HORIZONTAL_INFLINE]

    @property
    def vertical_infline(self) -> InfiniteLine:
        """Vertical infinite line visual"""
        return self._subvisuals[VERTICAL_INFLINE]

    def create_line(self, pos: float, vertical: bool, color: np.ndarray) -> None:
        """Create new visuals"""
        visual = InfiniteLine(pos, color=color, vertical=vertical, parent=self.parent)
        self.add_subvisual(visual)
        visual.transform = self._subvisuals[0].transform

    def remove_line(self, index: int) -> None:
        """Remove visual."""
        visual = self._subvisuals[3 + index]
        visual.parent = None
        self.remove_subvisual(visual)

    def remove_all_lines(self) -> None:
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
