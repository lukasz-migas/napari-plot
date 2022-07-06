"""Plotting interface."""
import napari_plot

viewer1d = napari_plot.Viewer()
# create vertical barchart
x = [0, 1, 2, 3]
y1 = [100, 120, 110, 130]
y2 = [120, 125, 115, 125]
viewer1d.bar(x, y1, face_color="green")
viewer1d.bar(x, y2, bottom=y1, face_color="yellow")

napari_plot.run()
