"""Mouse bindings"""


# TODO: this should draw temporary region of interest
def add(layer, event):
    """Add new infinite region."""
    if event.type == "mouse_press":
        pos_start = event.pos
        position_start = event.position

    while event.type != "mouse_release":
        yield

    x_dist, y_dist = pos_start - event.pos
    coord_start = layer.world_to_data(position_start)
    coord_end = layer.world_to_data(event.position)
    if abs(x_dist) < abs(y_dist):
        orientation = "horizontal"
        pos = [coord_start[0], coord_end[0]]
    else:
        orientation = "vertical"
        pos = [coord_start[1], coord_end[1]]
    layer.add([pos], orientation=[orientation])


def move(layer, event):
    """Move the currently drawn region to new location"""

    def _update(finished: bool = False):
        new_coordinates = layer.world_to_data(event.position)
        start_coordinates = new_coordinates - wh_half
        end_coordinates = new_coordinates + wh_half
        layer.move(start_coordinates, end_coordinates, finished)

    # on press, keep track of the original data
    if event.type == "mouse_press":
        wh = layer.data[1] - layer.data[0]
        wh_half = wh / 2
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


def select(layer, event):
    """Select new region in the canvas"""
    # on press, keep track of the start position
    if event.type == "mouse_press":
        start_coordinates = layer.world_to_data(event.position)
        yield

    # on mouse move
    while event.type == "mouse_move":
        end_coordinates = layer.world_to_data(event.position)
        layer.move(start_coordinates, end_coordinates, False)
        yield

    # on mouse release
    while event.type != "mouse_release":
        yield

    end_coordinates = layer.world_to_data(event.position)
    layer.move(start_coordinates, end_coordinates, True)
