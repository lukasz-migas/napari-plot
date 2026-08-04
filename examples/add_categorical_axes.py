"""Plot numeric data with categorical labels on both axes."""

import numpy as np

import napari_plot

viewer1d = napari_plot.Viewer()

categories = ["control", "low dose", "high dose"]
responses = ["decreased", "unchanged", "increased"]
viewer1d.add_scatter(
    np.asarray([[0, 0], [1, 1], [2, 2]]),
    name="response",
    size=20,
)

# Categories label the numeric positions 0, 1, ... and activate the scale.
viewer1d.axis.x_categories = categories
viewer1d.axis.y_categories = responses
viewer1d.axis.x_label = "treatment"
viewer1d.axis.y_label = "response"

if __name__ == "__main__":
    napari_plot.run()
