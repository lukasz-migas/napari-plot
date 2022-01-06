"""Mouse bindings"""
from copy import copy

import numpy as np

from ._infline_constants import Orientation


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
    # on press
    if event.type == "mouse_press":
        start_pos = event.pos
        yield

    # on move
    index = None
    while event.type == "mouse_move":
        x_dist, y_dist = start_pos - event.pos
        coordinates = layer.world_to_data(event.position)
        if abs(x_dist) > abs(y_dist):
            orientation = Orientation.HORIZONTAL
            pos = coordinates[0]
        else:
            orientation = Orientation.VERTICAL
            pos = coordinates[1]
        if index is None:
            index = layer._add_creating(pos, orientation=orientation)
        else:
            layer.move(index, pos, orientation)
        yield

    # on release
    if index is not None:
        layer.move(index, pos, orientation, True)


def select(layer, event):
    """Select lines in layer.

    This function should enable selection of infinite lines by either clicking on (or near) the line or dragging
    a rectangular box.
    """
    shift = "Shift" in event.modifiers
    # on press
    line_under_cursor, _ = _select(layer, event, shift)

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
        yield

    # on release
    shift = "Shift" in event.modifiers
    if not layer._is_moving and not layer._is_selecting and not shift:
        if line_under_cursor is not None:
            layer.selected_data = {line_under_cursor}
        else:
            layer.selected_data = set()
    elif layer._is_selecting:
        layer.selected_data = layer._data_view.lines_in_box(layer._drag_box)
        layer._is_selecting = False

    layer._drag_start = None
    layer._drag_box = None
    layer._set_highlight()

    if update_thumbnail:
        layer._update_thumbnail()


def _select(layer, event, shift: bool):
    """Select region(s) on mouse press. Allow for multiple selection if `shift=True`"""
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
    return region_under_cursor, vertex_under_cursor


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
