"""Mouse bindings"""
from copy import copy

import numpy as np


# TODO: this should draw temporary region of interest
def add(layer, event):
    """Add new infinite region."""
    print("add")
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
    shift = "Shift" in event.modifiers
    # on press
    value = layer.get_value(event.position, world=True)
    layer._moving_value = copy(value)
    region_under_cursor, vertex_under_cursor = value
    if vertex_under_cursor is None:
        if shift and region_under_cursor is not None:
            if region_under_cursor in layer.selected_data:
                layer.selected_data.remove(region_under_cursor)
            else:
                layer.selected_data.add(region_under_cursor)
        elif region_under_cursor is not None:
            if region_under_cursor not in layer.selected_data:
                layer.selected_data = {region_under_cursor}
        else:
            layer.selected_data = set()
    layer._set_highlight()

    # we don't update the thumbnail unless a shape has been moved
    update_thumbnail = False
    yield

    # on move
    while event.type == "mouse_move":
        coordinates = layer.world_to_data(event.position)
        layer._moving_coordinates = coordinates
        # Drag any selected shapes
        if len(layer.selected_data) == 0:
            _drag_selection_box(layer, coordinates)

        # if a shape is being moved, update the thumbnail
        if layer._is_moving:
            update_thumbnail = True
        yield

    # only emit data once dragging has finished
    # if layer._is_moving:
    #     layer.events.data(value=layer.data)

    # on release
    shift = "Shift" in event.modifiers
    if not layer._is_moving and not layer._is_selecting and not shift:
        if region_under_cursor is not None:
            layer.selected_data = {region_under_cursor}
        else:
            layer.selected_data = set()
    elif layer._is_selecting:
        layer.selected_data = layer._data_view.regions_in_box(layer._drag_box)
        layer._is_selecting = False
        layer._set_highlight()

    # layer._is_moving = False
    layer._drag_start = None
    layer._drag_box = None
    layer._moving_value = (None, None)
    layer._set_highlight()

    # layer._is_moving = False
    layer._set_highlight()

    if update_thumbnail:
        layer._update_thumbnail()


def _drag_selection_box(layer, coordinates):
    """Drag a selection box.

    Parameters
    ----------
    layer : napari.layers.Shapes
        Shapes layer.
    coordinates : tuple
        Position of mouse cursor in data coordinates.
    """
    # If something selected return
    if len(layer.selected_data) > 0:
        return

    coord = [coordinates[i] for i in layer._dims_displayed]

    # Create or extend a selection box
    layer._is_selecting = True
    if layer._drag_start is None:
        layer._drag_start = coord
    layer._drag_box = np.array([layer._drag_start, coord])
    layer._set_highlight()


def _move(layer, coordinates):
    """Moves object at given mouse position and set of indices.

    Parameters
    ----------
    layer : napari.layers.Shapes
        Shapes layer.
    coordinates : tuple
        Position of mouse cursor in data coordinates.
    """
    # If nothing selected return
    if len(layer.selected_data) == 0:
        return

    vertex = layer._moving_value[1]
