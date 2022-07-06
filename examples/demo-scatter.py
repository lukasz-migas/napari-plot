"""Scatter demo.

Example taken and adapted from:
https://www.python-graph-gallery.com/manhattan-plot-with-matplotlib
"""
import pandas as pd
from scipy.stats import uniform
from scipy.stats import randint
import numpy as np
import napari_plot

COLORS = ["darkred", "darkgreen", "darkblue", "gold"]

# sample data
df = pd.DataFrame(
    {
        "gene": ["gene-%i" % i for i in np.arange(10000)],
        "pvalue": uniform.rvs(size=10000),
        "chromosome": ["ch-%i" % i for i in randint.rvs(0, 12, size=10000)],
    }
)

# -log_10(pvalue)
df["neg_log10p"] = -np.log10(df.pvalue)
df.chromosome = df.chromosome.astype("category")
df.chromosome = df.chromosome.cat.set_categories(["ch-%i" % i for i in range(12)], ordered=True)
df = df.sort_values("chromosome")

# How to plot gene vs. -log10(pvalue) and colour it by chromosome?
df["ind"] = range(len(df))
df_grouped = df.groupby("chromosome")

# manhattan plot
viewer = napari_plot.Viewer()
x_labels = []
x_labels_pos = []
for num, (name, group) in enumerate(df_grouped):
    colors = COLORS[num % len(COLORS)]
    viewer.add_scatter(
        np.c_[group.neg_log10p, group.ind], edge_color=colors, face_color=colors, scaling=False, size=4, name=name
    )
    x_labels.append(name)
    x_labels_pos.append(group["ind"].iloc[-1] - (group["ind"].iloc[-1] - group["ind"].iloc[0]) / 2)

# Sadly we can't yet define categorical variables
# ax.set_xticks(x_labels_pos)
# ax.set_xticklabels(x_labels)

# set axis limits
viewer.camera.x_range = 0, len(df)
viewer.camera.y_range = 0, 3.5

# x axis label
viewer.axis.x_label = "Chromosome"

# show the graph
napari_plot.run()
