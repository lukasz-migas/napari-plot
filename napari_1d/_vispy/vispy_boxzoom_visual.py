"""Visual to illustrate user zoom."""
from typing import TYPE_CHECKING

import numpy as np
from vispy.scene.visuals import Mesh

if TYPE_CHECKING:
    from ..components.viewer_model import ViewerModel
    from .camera import LimitedPanZoomCamera


class VispyBoxZoomVisual:
    """Box zoom visual that displays single rectangular box."""

    def __init__(
        self,
        viewer: "ViewerModel",
        camera: "LimitedPanZoomCamera",
        parent=None,
        order=5e6,
    ):
        self._viewer = viewer
        self._camera = camera

        self.node = Mesh()
        self.node.order = order
        if parent:
            parent.add(self.node)

        self._viewer.boxzoom.events.visible.connect(self._on_visible_change)
        self._viewer.boxzoom.events.opacity.connect(self._on_opacity_change)
        self._viewer.boxzoom.events.color.connect(self._on_color_change)
        self._viewer.boxzoom.events.rect.connect(self._on_data_change)

        self._on_visible_change()
        self._on_color_change()
        self._on_opacity_change()
        self._on_data_change()

    def _on_visible_change(self, _evt=None):
        """Change span visibility"""
        self.node.visible = self._viewer.boxzoom.visible

    def _on_opacity_change(self, _evt=None):
        """Change span visibility"""
        self.node.opacity = self._viewer.boxzoom.opacity

    def _on_color_change(self, _event=None):
        """Change the appearance of the data"""
        self.node.set_data(color=self._viewer.boxzoom.color)
        self.node.update()

    def _on_data_change(self, _event=None):
        """Set data"""
        x0, x1, y0, y1 = self._viewer.boxzoom.rect
        corner = np.array([y0, x0])
        size_v = np.zeros(2)
        size_v[0] = abs(y1 - y0) / 4
        size_h = np.zeros(2)
        size_h[1] = abs(x1 - x0) / 4
        data = np.array([corner, corner + size_v, corner + size_h + size_v, corner + size_h])
        # print(data)
        # data = np.array(
        #     [
        #         [y0, x0],
        #         [y0, x1],
        #         [y1, x1],
        #         [y1, x0],
        #         [50, 0],
        #         [0, 30],
        #         # [3, 0],
        #         # [0, 1]
        #         # [0, x0 - x1],
        #         # [y0 - y1, 0],
        #     ]
        # )
        # print(data)

        self.node.set_data(data, color=self._viewer.boxzoom.color)
        self.node.update()
