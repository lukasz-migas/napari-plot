"""Mouse bindings"""

from __future__ import annotations

import typing as ty
from copy import copy

import numpy as np

from napari_plot.layers.infline._infline_constants import Orientation

if ty.TYPE_CHECKING:
    from vispy.app.canvas import MouseEvent

    from napari_plot.layers.infline import InfLine


def highlight(layer, event):
    """Highlight hovered lines."""
    layer._set_highlight()


def add(layer: InfLine, event: MouseEvent):
    """Add a new infinite line at the clicked position."""
    # on press
    start_pos = event.pos
    yield

    # on move
    pos, orientation = None, None
    while event.type == "mouse_move":
        coordinates = layer.world_to_data(event.position)
        # if the Ctrl key is pressed, orientation is vertical
        if "Control" in event.modifiers:
            orientation = Orientation.VERTICAL
        # if the Shift key is pressed, orientation is horizontal
        elif "Shift" in event.modifiers:
            orientation = Orientation.HORIZONTAL
        # otherwise, it's based on distance
        else:
            x_dist, y_dist = start_pos - event.pos
            orientation = (
                Orientation.HORIZONTAL
                if abs(x_dist) > abs(y_dist)
                else Orientation.VERTICAL
            )

        pos = coordinates[1] if orientation == "vertical" else coordinates[0]
        layer._add_move(pos, orientation=orientation)
        yield

    # on release
    if pos:
        layer._add_finish(pos, orientation=orientation)


def move(layer: InfLine, event: MouseEvent):
    """Move currently selected line to new location."""
    # above, user should have selected single line and then can move it left-or-right or up-or-down
    index, data, orientation = None, None, None
    n = len(layer.selected_data)
    if n > 0:
        index = next(iter(layer.selected_data))
        data, orientation = layer.data[index], layer.orientation[index]
        layer.selected_data = {index}
        layer._set_highlight()
    yield

    # on move
    while event.type == "mouse_move":
        if data is not None:
            coordinates = layer.world_to_data(event.position)
            layer._moving_coordinates = coordinates
            layer.move(
                index,
                coordinates[1] if orientation == "vertical" else coordinates[0],
                finished=False,
            )
        yield

    # on release
    if data is not None:
        coordinates = layer.world_to_data(event.position)
        layer._moving_coordinates = coordinates
        layer.move(
            index,
            coordinates[1] if orientation == "vertical" else coordinates[0],
            finished=True,
        )
        layer._set_highlight()
        layer._update_thumbnail()


def select(layer: InfLine, event: MouseEvent):
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


def _select(layer: InfLine, event: MouseEvent, shift: bool):
    """Select region(s) on mouse press. Allow for multiple selection if `shift=True`"""
    value = layer.get_value(event.position, world=True)
    layer._moving_value = copy(value)
    line_under_cursor, vertex_under_cursor = value
    if vertex_under_cursor is None:
        if shift and line_under_cursor is not None:
            if line_under_cursor in layer.selected_data:
                layer.selected_data.remove(line_under_cursor)
            else:
                layer.selected_data.add(line_under_cursor)
        elif line_under_cursor is not None:
            if line_under_cursor not in layer.selected_data:
                layer.selected_data = {line_under_cursor}
        else:
            layer.selected_data = set()
    layer._set_highlight()
    return line_under_cursor, vertex_under_cursor


def _drag_selection_box(layer: InfLine, coordinates: tuple[int, int]) -> None:
    """Drag a selection box.

    Parameters
    ----------
    layer : napari.layers.Shapes
        Shapes layer.
    coordinates : tuple
        Position of mouse cursor in data coordinates.
    """
    # If something selected return
    coord = [coordinates[i] for i in layer._slice_input.displayed]

    # Create or extend a selection box
    layer._is_selecting = True
    if layer._drag_start is None:
        layer._drag_start = coord
    layer._drag_box = np.array([layer._drag_start, coord])
    layer._set_highlight()
