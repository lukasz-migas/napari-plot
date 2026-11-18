"""Seaborn-style statistical plots built from napari-plot layers.

Every function takes the viewer as its first argument and returns the list of layers it created. The same
functions are available as viewer methods, e.g. ``viewer.boxplot(df, x="day", y="total_bill", hue="smoker")``.
"""

from napari_plot.stats.categorical import barplot, boxenplot, boxplot, stripplot, swarmplot, violinplot
from napari_plot.stats.distributions import distplot, histplot, kdeplot
from napari_plot.stats.matrix import clustermap, heatmap
from napari_plot.stats.relational import lineplot, relplot, scatterplot

__all__ = [
    "barplot",
    "boxenplot",
    "boxplot",
    "clustermap",
    "distplot",
    "heatmap",
    "histplot",
    "kdeplot",
    "lineplot",
    "relplot",
    "scatterplot",
    "stripplot",
    "swarmplot",
    "violinplot",
]
