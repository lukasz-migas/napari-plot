"""Error bars
==============

Show asymmetric measurement intervals on calibration standards.

.. tags:: bars-and-histograms
"""

import napari_plot

concentration = [1, 2, 4, 8]
intensity = [12, 23, 45, 86]

viewer = napari_plot.Viewer()
viewer.axis.x_label = "Concentration (uM)"
viewer.axis.y_label = "Ion intensity"
viewer.errorbar(
    concentration,
    intensity,
    xerr=0.2,
    yerr=[[1, 2, 4, 5], [2, 3, 6, 8]],
    color="orange",
    cap_size=8,
    width=2,
    name="Measurement intervals",
)
viewer.scatter(concentration, intensity, face_color="orange", size=7, name="Standards")
viewer.legend.visible = True

if __name__ == "__main__":
    napari_plot.run()
