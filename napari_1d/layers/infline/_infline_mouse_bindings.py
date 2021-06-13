"""Mouse bindings"""


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
