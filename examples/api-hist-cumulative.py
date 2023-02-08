"""Example of histogram where cumulative distribution function is computed.

Example taken and adapted from:
https://matplotlib.org/stable/gallery/statistics/histogram_cumulative.html
"""
import numpy as np
import napari_plot

np.random.seed(19680801)

mu = 200
sigma = 25
n_bins = 50
x = np.random.normal(mu, sigma, size=100)

viewer1d = napari_plot.Viewer()

# plot the cumulative histogram
n, bins, patches = viewer1d.hist(
    x,
    n_bins,
    density=True,
    # histtype="step", # not supported yet
    cumulative=True,
    label="Empirical",
    alpha=0.4,
)

# Add a line showing the expected distribution.
y = (1 / (np.sqrt(2 * np.pi) * sigma)) * np.exp(-0.5 * (1 / sigma * (bins - mu)) ** 2)
y = y.cumsum()
y /= y[-1]

viewer1d.plot(bins, y, "w--", linewidth=1.5, label="Theoretical")

# Overlay a reversed cumulative histogram.
viewer1d.hist(
    x,
    bins=bins,
    density=True,
    # histtype="step", # not supported yet
    cumulative=-1,
    label="Reversed emp.",
    alpha=0.4,
)

# tidy up the figure
viewer1d.grid_lines.visible = True
# ax.legend(loc='right')
# ax.set_title('Cumulative step histograms')
viewer1d.axis.x_label = "Annual rainfall (mm)"
viewer1d.axis.y_label = "Likelihood of occurrence"
napari_plot.run()
