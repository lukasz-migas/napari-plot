"""Create simple callback that modifies the line visual."""

import napari
import numpy as np
from skimage import data, measure

import napari_plot
from napari_plot._qt.qt_viewer import QtViewer


def _get_line_data(image, start, end):
    return measure.profile_line(image, start, end, mode="nearest")


viewer = napari.Viewer()
chelsea = data.astronaut().mean(-1)
viewer.add_image(chelsea)
shapes_layer = viewer.add_shapes(
    [np.array([[11, 13], [250, 313]]), np.array([[100, 10], [10, 345]])],
    shape_type="line",
    edge_width=5,
    edge_color="coral",
    face_color="royalblue",
)
shapes_layer.mode = "select"

viewer1d = napari_plot.ViewerModel1D()
viewer1d.axis.y_label = "Intensity"
viewer1d.axis.x_label = ""
viewer1d.text_overlay.visible = True
viewer1d.text_overlay.position = "top_right"

qt_viewer = QtViewer(viewer1d)

lines = []
for i, line in enumerate(shapes_layer.data):
    y = _get_line_data(chelsea, *line)
    lines.append(viewer1d.add_line(np.c_[np.arange(len(y)), y], name=str(i)))


# hook the lines up to events
def _profile_lines(image, shape_layer):
    # only a single line for this example
    for i, line in enumerate(shape_layer.data):
        if i in shape_layer._selected_data:
            y = _get_line_data(image, *line)
            lines[i].data = np.c_[np.arange(len(y)), y]


@shapes_layer.mouse_drag_callbacks.append
def _profile_lines_drag(layer, event):
    _profile_lines(chelsea, layer)
    yield
    while event.type == "mouse_move":
        _profile_lines(chelsea, layer)
        yield


viewer.window.add_dock_widget(qt_viewer, area="bottom", name="Line Widget")

if __name__ == "__main__":
    napari.run()
