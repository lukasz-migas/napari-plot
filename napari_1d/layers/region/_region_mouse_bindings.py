"""Mouse bindings"""
from copy import copy

import numpy as np

from ._region_constants import Orientation
from ._region_utils import preprocess_region


def highlight(layer, event):
    """Highlight hovered regions."""
    layer._set_highlight()


# TODO: this should draw temporary region of interest
def add(layer, event):
    """Add new infinite region."""
    # on press
    pos_start = event.pos
    position_start = event.position
    yield

    # on move
    index = None
    while event.type == "mouse_move":
        x_dist, y_dist = pos_start - event.pos
        coord_start = layer.world_to_data(position_start)
        coord_end = layer.world_to_data(event.position)
        if abs(x_dist) < abs(y_dist):
            orientation = Orientation.HORIZONTAL
            pos = [coord_start[0], coord_end[0]]
        else:
            orientation = Orientation.VERTICAL
            pos = [coord_start[1], coord_end[1]]
        if index is None:
            index = layer._add_creating(pos, orientation=orientation)
        else:
            layer.move(index, preprocess_region(pos, orientation), orientation=orientation)
        yield

    # on release
    layer._finish_drawing()


def edit(layer, event):
    """Edit layer by first selecting and then drawing new version of the region."""


def move(layer, event):
    """Move region by first selecting and then moving along the axis."""
    # on press
    _select(layer, event, False)
    # above, user should have selected single region and then can move it left-or-right or up-or-down
    data, orientation, wh_half = None, None, None
    if len(layer.selected_data) > 0:
        index = list(layer.selected_data)[0]
        data, orientation = layer.data[index], layer.orientation[index]
        wh_half = _get_half(data, orientation)
    yield

    # on move
    while event.type == "mouse_move":
        if data is not None:
            coordinates = layer.world_to_data(event.position)
            layer._moving_coordinates = coordinates
            layer.move(index, _get_region(coordinates, wh_half, orientation), orientation)
        yield

    # on release
    layer.selected_data = set()  # clear selection
    layer._set_highlight()
    layer._update_thumbnail()
    if data is not None:
        coordinates = layer.world_to_data(event.position)
        layer._moving_coordinates = coordinates
        layer.move(index, _get_region(coordinates, wh_half, orientation), orientation, True)


def select(layer, event):
    """Select new region in the canvas"""
    shift = "Shift" in event.modifiers
    # on press
    region_under_cursor, _ = _select(layer, event, shift)

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
        if region_under_cursor is not None:
            layer.selected_data = {region_under_cursor}
        else:
            layer.selected_data = set()
    elif layer._is_selecting:
        layer.selected_data = layer._data_view.regions_in_box(layer._drag_box)
        layer._is_selecting = False
        layer._set_highlight()

    layer._drag_start = None
    layer._drag_box = None
    layer._set_highlight()

    if update_thumbnail:
        layer._update_thumbnail()


def _select(layer, event, shift: bool):
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


def _get_half(data: np.ndarray, orientation: Orientation):
    """Get data along dimension."""
    if orientation == Orientation.HORIZONTAL:
        return abs(data[0, 0] - data[2, 0]) / 2
    return abs(data[0, 1] - data[1, 1]) / 2


def _get_region(coordinates, wh_half: float, orientation: Orientation):
    """Get region."""
    if orientation == Orientation.HORIZONTAL:
        return preprocess_region((coordinates[0] - wh_half, coordinates[0] + wh_half), orientation)
    return preprocess_region((coordinates[1] - wh_half, coordinates[1] + wh_half), orientation)
