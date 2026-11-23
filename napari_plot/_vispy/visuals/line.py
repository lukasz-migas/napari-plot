"""Line visual and screen-space dash rendering."""

from __future__ import annotations

from typing import Any

import numpy as np
from vispy.scene.visuals import Line as LineVisual  # noqa: F401
from vispy.visuals.line.line import _AggLineVisual


class ScreenDashLine(_AggLineVisual):
    """Use document-pixel arc length for VisPy's AGG dash atlas."""

    def _prepare_draw(self, view: Any) -> bool | None:
        self._document_transform = view.get_transform("visual", "document")
        return super()._prepare_draw(view)

    def _agg_bake(self, vertices: np.ndarray, color: np.ndarray, closed: bool = False) -> tuple[np.ndarray, np.ndarray]:
        baked, indices = super()._agg_bake(vertices, color, closed)
        points = self._document_transform.map(vertices)[:, :2]
        if closed and len(baked) > 4 * (len(points) - 1):
            points = np.vstack((points, points[0]))
        distances = np.linalg.norm(np.diff(points, axis=0), axis=1)
        np.nan_to_num(distances, copy=False, posinf=0, neginf=0)
        lengths = np.r_[0, np.cumsum(distances)]
        # AGG expands each segment to four vertices, each carrying the range in path coordinates.
        baked["a_segment"] = np.repeat(np.column_stack((lengths[:-1], lengths[1:])), 4, axis=0)
        baked["alength"] = lengths[-1]
        return baked, indices
