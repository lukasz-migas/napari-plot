"""Single access point for the seaborn pieces reused by napari-plot.

Several of these symbols are private seaborn API, which is why ``seaborn`` is pinned to ``>=0.13.2,<0.14``.
Keeping every seaborn import in this module means an upgrade can only break in one place, and
``tests/stats/test_seaborn_adapter.py`` exercises each symbol.
"""

from __future__ import annotations

from seaborn import color_palette, light_palette, rugplot
from seaborn._base import categorical_order
from seaborn._statistics import KDE, EstimateAggregator, Histogram, LetterValues
from seaborn.categorical import Beeswarm
from seaborn.matrix import ClusterGrid, _DendrogramPlotter, _HeatMapper
from seaborn.regression import _RegressionPlotter
from seaborn.utils import relative_luminance

RegressionPlotter = _RegressionPlotter

__all__ = [
    "KDE",
    "Beeswarm",
    "ClusterGrid",
    "EstimateAggregator",
    "Histogram",
    "LetterValues",
    "_DendrogramPlotter",
    "_HeatMapper",
    "categorical_order",
    "color_palette",
    "light_palette",
    "relative_luminance",
    "rugplot",
]
