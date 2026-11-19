"""Fixed 24-pixel glyphs, centered by napari in the layer-list thumbnail."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

WHITE = (1.0, 1.0, 1.0, 1.0)

_ROW, _COL = np.ogrid[:24, :24]
_PLOT_WIDTH = (_COL >= 2) & (_COL < 22)


def _rect(top: int, bottom: int, left: int, right: int) -> NDArray[np.bool_]:
    mask = np.zeros((24, 24), dtype=bool)
    mask[top:bottom, left:right] = True
    return mask


def _profile(rows: ArrayLike) -> NDArray[np.float64]:
    return np.interp(_COL, [2, 7, 11, 16, 21], rows)


_TRACE = _profile([17, 12, 14, 5, 8])
LINE = _PLOT_WIDTH & (np.abs(_ROW - _TRACE) <= 1.2)
MULTILINE = (_PLOT_WIDTH & (np.abs(_ROW - _profile([10, 5, 7, 4, 5])) <= 1)) | (
    _PLOT_WIDTH & (np.abs(_ROW - _profile([19, 15, 18, 11, 14])) <= 1)
)
AREAS = _PLOT_WIDTH & (_ROW >= _TRACE) & (_ROW < 21)
BAND = _PLOT_WIDTH & (_profile([14, 9, 11, 4, 7]) <= _ROW) & (_profile([20, 16, 19, 12, 13]) >= _ROW)
BAR = _rect(13, 21, 3, 8) | _rect(5, 21, 10, 15) | _rect(9, 21, 17, 22)
CENTROIDS = _rect(15, 21, 3, 5) | _rect(6, 21, 8, 10) | _rect(11, 21, 13, 15) | _rect(3, 21, 19, 21)
ERROR_BAR = (
    _rect(9, 21, 4, 6)
    | _rect(9, 11, 2, 8)
    | _rect(19, 21, 2, 8)
    | _rect(3, 17, 11, 13)
    | _rect(3, 5, 9, 15)
    | _rect(15, 17, 9, 15)
    | _rect(6, 15, 18, 20)
    | _rect(6, 8, 16, 22)
    | _rect(13, 15, 16, 22)
)
INF_LINE = _rect(2, 22, 11, 13)
REGION = _rect(2, 22, 6, 8) | _rect(2, 22, 16, 18) | (_rect(2, 22, 8, 16) & ((_ROW + _COL) % 5 == 0))
RECTANGLES = _rect(5, 19, 2, 22) & ~_rect(7, 17, 4, 20)
TEXT = _rect(5, 8, 4, 20) | _rect(8, 19, 11, 14)

SCATTER = np.zeros((24, 24), dtype=bool)
for _y, _x in ((17, 5), (12, 8), (19, 11), (7, 13), (12, 17), (5, 20), (16, 21)):
    SCATTER |= (_ROW - _y) ** 2 + (_COL - _x) ** 2 <= 2
