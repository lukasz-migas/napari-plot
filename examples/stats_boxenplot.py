"""Letter-value plots
===============

Letter-value (boxen) plots show more quantiles than a box plot for large samples.

.. tags:: statistical-plots, box
"""

import numpy as np

import napari_plot

rng = np.random.default_rng(0)
samples = {
    "normal": rng.normal(0, 1, 5000),
    "skewed": rng.lognormal(0, 0.6, 5000) - 1,
    "bimodal": np.concatenate((rng.normal(-1.5, 0.5, 2500), rng.normal(1.5, 0.5, 2500))),
}

viewer = napari_plot.Viewer()
# Wide-form input: each dict key becomes a category.
viewer.boxenplot(samples, palette="Set2")

if __name__ == "__main__":
    napari_plot.run()
