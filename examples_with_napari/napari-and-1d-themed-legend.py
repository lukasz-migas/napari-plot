"""Match plot colors to the napari theme
===========================

Embed a plot and switch the napari theme to see its axes and legend update.

.. tags:: napari-integration
"""

import napari
import numpy as np

from napari_plot import NapariPlotWidget

viewer = napari.Viewer(title="Image and intensity profile")
viewer.theme = "light"
rows, cols = np.ogrid[-1:1:80j, -1:1:120j]
image = np.exp(-4 * (rows**2 + cols**2))
viewer.add_image(image, name="Synthetic spot")

widget = NapariPlotWidget(viewer)
viewer.window.add_dock_widget(widget, area="bottom", name="Intensity profiles")
plot = widget.viewer_plot
plot.plot(image[40], color="steelblue", name="Center row")
plot.plot(image[20], color="darkorange", name="Upper row")
plot.axis.x_label = "Column"
plot.axis.y_label = "Intensity"
plot.set_legend_from_layers(title="Image profiles", ncols=2, outside=True)
plot.reset_view()

if __name__ == "__main__":
    napari.run()
