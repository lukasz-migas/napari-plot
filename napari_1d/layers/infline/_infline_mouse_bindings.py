"""Mouse bindings"""


def highlight(layer, event):
    """Highlight hovered lines."""
    layer._set_highlight()


def move(layer, event):
    """Move the currently drawn region to new location"""

    def _update(finished: bool = False):
        new_coordinates = layer.world_to_data(event.position)
        layer.move(new_coordinates, finished)

    # on press, keep track of the original data
    if event.type == "mouse_press":
        _update()
        yield

    # on mouse move
    while event.type == "mouse_move":
        _update()
        yield

    # on mouse release
    while event.type != "mouse_release":
        yield
    _update(True)


def add(layer, event):
    """Add a new infinite line at the clicked position."""
    if event.type == "mouse_press":
        start_pos = event.pos
        position = event.position

    while event.type != "mouse_release":
        yield

    x_dist, y_dist = start_pos - event.pos
    coordinates = layer.world_to_data(position)
    if abs(x_dist) > abs(y_dist):
        orientation = "horizontal"
        pos = coordinates[0]
    else:
        orientation = "vertical"
        pos = coordinates[1]
    layer.add([pos], [orientation])


def select(layer, event):
    """Add layer."""
