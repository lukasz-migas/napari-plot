"""Mouse bindings."""

from __future__ import annotations

import typing as ty
from copy import copy

import numpy as np

from napari_plot.layers.region._region_constants import Orientation

if ty.TYPE_CHECKING:
    from vispy.app.canvas import MouseEvent

    from napari_plot.layers.region import Region


def highlight(layer: Region, event: MouseEvent) -> None:
    """Highlight hovered regions."""
    layer._set_highlight()


def add(layer: Region, event: MouseEvent) -> ty.Generator[None, None, None]:
    """Add new infinite region."""
    # on press
    pos_start = event.pos
    position_start = event.position
    coord_start = layer.world_to_data(position_start)
    layer._is_creating = True
    yield

    # on move
    pos, orientation = None, None
    while event.type == "mouse_move":
        coord_end = layer.world_to_data(event.position)

        # if the Ctrl key is pressed, orientation is vertical
        if "Control" in event.modifiers:
            orientation = Orientation.VERTICAL
        # if the Shift key is pressed, orientation is horizontal
        elif "Shift" in event.modifiers:
            orientation = Orientation.HORIZONTAL
        # otherwise, it's based on distance
        else:
            x_dist, y_dist = pos_start - event.pos
            orientation = Orientation.HORIZONTAL if abs(x_dist) < abs(y_dist) else Orientation.VERTICAL

        pos = [coord_start[1], coord_end[1]] if orientation == "vertical" else [coord_start[0], coord_end[0]]
        layer._add_move(pos, orientation=orientation)
        yield

    # on release
    if pos:
        layer._add_finish(pos, orientation=orientation)


def select(layer: Region, event: MouseEvent) -> ty.Generator[None, None, None]:
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

    layer._drag_start = None
    layer._drag_box = None
    layer._set_highlight()
    if update_thumbnail:
        layer._update_thumbnail()


def edit(layer: Region, event: MouseEvent) -> ty.Generator[None, None, None]:
    """Edit a region by first selecting and then drawing new version of the region."""
    if len(layer.selected_data) == 1:
        # on press
        index = next(iter(layer.selected_data))
        orientation = layer.orientation[index]
        start_coordinates = layer.world_to_data(event.position)
        yield

        # on move
        while event.type == "mouse_move":
            current_coordinates = layer.world_to_data(event.position)
            if orientation == Orientation.HORIZONTAL:
                pos = [start_coordinates[0], current_coordinates[0]]
            else:
                pos = [start_coordinates[1], current_coordinates[1]]
            layer.move(index, pos, orientation=orientation)
            yield

        # on release
        layer._set_highlight()
        layer._update_thumbnail()
        layer.mode = "select"


def move(layer: Region, event: MouseEvent) -> ty.Generator[None, None, None]:
    """Move region by first selecting and then moving along the axis.

    The method will move the regions in the direction of the mouse movement by the amount from 'start' to finish'
    """
    # on press
    # above, user should have selected single region and then can move it left-or-right or up-or-down
    tmp = {}
    start_coordinates = layer.world_to_data(event.position)
    for index in layer.selected_data:
        data = layer.data[index]
        tmp[index] = {
            "data": data,
            "orientation": layer.orientation[index],
        }
    yield

    # on move
    while event.type == "mouse_move":
        current_coordinates = layer.world_to_data(event.position)
        vert_diff, horz_diff = start_coordinates - current_coordinates
        for index, tmp_ in tmp.items():
            orientation = tmp_["orientation"]
            diff = vert_diff if orientation == Orientation.HORIZONTAL else horz_diff
            layer.move(index, tmp_["data"] - diff, orientation)
        yield

    # on release
    if tmp:
        current_coordinates = layer.world_to_data(event.position)
        vert_diff, horz_diff = start_coordinates - current_coordinates
        for index, tmp_ in tmp.items():
            orientation = tmp_["orientation"]
            diff = vert_diff if orientation == Orientation.HORIZONTAL else horz_diff
            layer.move(index, tmp_["data"] - diff, orientation)
        layer._set_highlight()
        layer._update_thumbnail()
        del tmp


def _select(layer: Region, event: MouseEvent, shift: bool) -> ty.Tuple[ty.Optional[int], ty.Optional[int]]:
    """Select region(s) on mouse press. Allow for multiple selection if `shift=True`"""
    # TODO: update current_face_color
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


def _drag_selection_box(layer: Region, coordinates: tuple[int, int]) -> None:
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

    coord = [coordinates[i] for i in layer._slice_input.displayed]

    # Create or extend a selection box
    layer._is_selecting = True
    if layer._drag_start is None:
        layer._drag_start = coord
    layer._drag_box = np.array([layer._drag_start, coord])
    layer._set_highlight()
