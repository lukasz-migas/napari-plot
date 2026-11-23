"""Practice editing directly on a plot with the layer controls.

With Samples selected, click the canvas to add a point. Use Select to drag or
select points, then use Delete to remove them. Select the Regions layer and use
Add to draw a rectangle or Edit to move one. Hold Shift while dragging to resize.
Use Move on the Labels layer to drag the text. To remove a bar, select Counts,
Shift-click a bar, and click Delete in its layer controls.
"""

import napari_plot

viewer = napari_plot.Viewer(title="Editing plot layers")
viewer.drag_tool.active = "none"
viewer.vbar([6, 7, 8], [1.4, 2.2, 1.1], color="steelblue", width=0.55, name="Counts")
viewer.rectangle((0.7, 0.7), 3.8, 2, color="cyan", name="Regions")
viewer.text([1.1, 6], [3.0, 3.0], ["Sampling area", "Counts"], alignment="left", name="Labels")
samples = viewer.scatter(
    [1.2, 2.1, 3.3, 4.0], [1.1, 2.0, 1.4, 1.8], color="orange", size=12, scaling=False, name="Samples"
)
viewer.layers.selection.select_only(samples)
samples.mode = "add"
viewer.axis.x_label = "Position"
viewer.axis.y_label = "Value"
viewer.xlim = (0, 9)
viewer.ylim = (0, 3.5)

if __name__ == "__main__":
    napari_plot.run()
