"""Mouse bindings to the viewer"""

import typing as ty
from functools import partial

import numpy as np

from napari_plot.components.tools import Shape

if ty.TYPE_CHECKING:
    from napari_plot.viewer import Viewer

ACTIVE_COLOR: tuple = (1.0, 0.0, 0.0, 1.0)
AUTO_SPAN_PIXEL_THRESHOLD: int = 20
LASSO_VERTEX_DISTANCE: int = 10


def polygon_select(viewer: "Viewer", event):
    """Enable polygon tool.

    This tool gives the user an option to draw a polygon in the canvas that will be used to select data in currently
    selected layer (or layers).

    The action is as follow:
        1. Left mouse click adds a point to the polygon.
        2. Left mouse click + CTRL removes the last point
        3. Left mouse click + SHIFT removes the nearest point
        4. Right mouse click cancels polygon
    """
    # on press
    viewer.drag_tool.tool.finished = False
    if event.button == 1:  # left-click
        if "Control" in event.modifiers:
            viewer.drag_tool.tool.remove_point(-1)
        elif "Shift" in event.modifiers:
            viewer.drag_tool.tool.remove_nearby_point(event.position)
        else:
            viewer.drag_tool.tool.add_point(event.position)
        viewer.drag_tool.tool.visible = True
    elif event.button == 2:  # right-click
        viewer.drag_tool.tool.clear()
        viewer.drag_tool.tool.visible = False
    yield

    # on mouse move
    while event.type == "mouse_move":
        yield

    # on release
    viewer.drag_tool.tool.finished = True
    viewer.drag_tool.vertices = viewer.drag_tool.tool.data
    # viewer.drag_tool.tool.visible = False


def lasso_select(viewer: "Viewer", event):
    """Enable polygon tool.

    This tool gives the user an option to draw a polygon in the canvas that will be used to select data in currently
    selected layer (or layers).

    The action is as follow:
        1. Left mouse click creates starting point.
        2. Left mouse drag keeps on adding points
        3. Right mouse click cancels lasso.
    """
    # on press
    viewer.drag_tool.tool.finished = False
    if event.button == 1:  # left-click
        viewer.drag_tool.tool.add_point(event.position)
        viewer.drag_tool.tool.visible = True
    elif event.button == 2:  # right-click
        viewer.drag_tool.tool.clear()
        viewer.drag_tool.tool.visible = False
    yield

    # on mouse move
    last_pos = event.pos
    while event.type == "mouse_move":
        if event.button == 1:
            position_diff = np.linalg.norm(event.pos - last_pos)
            if position_diff > LASSO_VERTEX_DISTANCE:
                viewer.drag_tool.tool.add_point(event.position)
                last_pos = event.pos
        yield
    # on release
    viewer.drag_tool.tool.finished = True
    viewer.drag_tool.vertices = viewer.drag_tool.tool.data
    # viewer.drag_tool.tool.visible = False


def box_select(viewer: "Viewer", event):
    """Enable box zoom."""
    # on press
    if event.button == 1:  # left-click
        viewer.drag_tool.tool.finished = False
        viewer.drag_tool.tool.visible = True
        viewer.drag_tool.tool.shape = Shape.BOX
    elif event.button == 2:  # right-click
        viewer.drag_tool.tool.position = (0, 0, 0, 0)
        viewer.drag_tool.tool.visible = False
    color = viewer.drag_tool.tool.color
    yield

    # on mouse move
    while event.type == "mouse_move":
        yield

    # on release
    viewer.drag_tool.tool.color = color
    viewer.drag_tool.vertices = viewer.drag_tool.tool.data
    viewer.drag_tool.tool.finished = True
    # viewer.drag_tool.tool.position = (0, 0, 0, 0)
    # viewer.drag_tool.tool.visible = False


def _get_auto_shape(press_pos: np.ndarray, pos: np.ndarray) -> Shape:
    """Determine the shape of the zoom tool based on the on-screen (pixel) size of the drag.

    Spans are only returned when the drag is essentially flat in one direction, otherwise it's a box.
    """
    dx, dy = np.abs(np.asarray(pos[:2], dtype=float) - np.asarray(press_pos[:2], dtype=float))
    # drag is too small to determine user intent
    if dx < AUTO_SPAN_PIXEL_THRESHOLD and dy < AUTO_SPAN_PIXEL_THRESHOLD:
        return Shape.BOX
    # minimal change in y-position, lets show it as vertical span
    if dy < AUTO_SPAN_PIXEL_THRESHOLD:
        return Shape.VERTICAL
    # minimal change in x-position, lets show it as horizontal span
    if dx < AUTO_SPAN_PIXEL_THRESHOLD:
        return Shape.HORIZONTAL
    return Shape.BOX


def _get_span_position(
    shape: Shape,
    position: tuple[float, float, float, float],
    view_rect: tuple[float, float, float, float],
) -> np.ndarray:
    """Return position that respects the shape of the tool.

    Vertical span uses the entire visible y-axis range and horizontal span uses the entire visible x-axis range.
    """
    x0, x1, y0, y1 = position
    vx0, vx1, vy0, vy1 = view_rect
    if shape == Shape.VERTICAL:
        y0, y1 = vy0, vy1
    elif shape == Shape.HORIZONTAL:
        x0, x1 = vx0, vx1
    return np.asarray([x0, x1, y0, y1])


def _set_modifier_range(viewer: "Viewer", modifiers, position: tuple[float, float, float, float]) -> bool:
    """Set the range of the modifier that is currently active."""
    if not modifiers:
        return False
    if "Control" in modifiers:
        viewer.drag_tool.ctrl = position
    elif "Shift" in modifiers:
        viewer.drag_tool.shift = position
    elif "Alt" in modifiers:
        viewer.drag_tool.alt = position
    else:
        viewer.drag_tool.ctrl = (0, 0, 0, 0)
        viewer.drag_tool.shift = (0, 0, 0, 0)
        viewer.drag_tool.alt = (0, 0, 0, 0)
    return True


def box_zoom_auto(viewer: "Viewer", event):
    """Enable box zoom."""

    def _get_shape():
        # handle modifiers first
        if "Alt" in event.modifiers:
            return Shape.BOX
        if "Control" in event.modifiers:
            return Shape.VERTICAL
        if "Shift" in event.modifiers:
            return Shape.HORIZONTAL
        return _get_auto_shape(press_pos, event.pos)

    # make sure box is visible
    if not viewer.camera.mouse_zoom or not viewer.camera.mouse_pan:
        return

    if not viewer.drag_tool.tool.visible:
        viewer.drag_tool.tool.visible = True

    # on press
    press_pos = np.asarray(event.pos)
    view_rect = viewer.camera.rect
    color = viewer.drag_tool.tool.color
    viewer.drag_tool.tool.shape = _get_shape()
    yield

    # on mouse move
    while event.type == "mouse_move":
        viewer.drag_tool.tool.shape = _get_shape()
        yield

    # on release
    shape = viewer.drag_tool.tool.shape = _get_shape()
    viewer.drag_tool.tool.color = color
    position = _get_span_position(shape, viewer.drag_tool.tool.position, view_rect)
    viewer.drag_tool.tool.visible = False
    viewer.drag_tool.tool.position = (0, 0, 0, 0)
    viewer.events.span(position=position)


def box_zoom_auto_trigger(viewer: "Viewer", event):
    """Enable box zoom."""
    # make sure box is visible
    if not viewer.camera.mouse_zoom or not viewer.camera.mouse_pan:
        return

    # on press
    press_pos = np.asarray(event.pos)
    view_rect = viewer.camera.rect
    color = viewer.drag_tool.tool.color
    viewer.drag_tool.tool.visible = True
    viewer.drag_tool.tool.shape = Shape.BOX
    yield

    # on mouse move
    while event.type == "mouse_move":
        viewer.drag_tool.tool.shape = _get_auto_shape(press_pos, event.pos)
        viewer.drag_tool.tool.color = ACTIVE_COLOR if event.modifiers else color
        yield

    # on release
    shape = viewer.drag_tool.tool.shape = _get_auto_shape(press_pos, event.pos)
    viewer.drag_tool.tool.visible = False
    viewer.drag_tool.tool.color = color
    viewer.drag_tool.selection_active = bool(event.modifiers)
    position = _get_span_position(shape, viewer.drag_tool.tool.position, view_rect)
    _set_modifier_range(viewer, event.modifiers, position)
    viewer.drag_tool.tool.position = (0, 0, 0, 0)
    viewer.events.span(position=position)


def box_zoom_shape(shape: Shape, viewer: "Viewer", event):
    """Enable box zoom."""
    # on press
    view_rect = viewer.camera.rect
    color = viewer.drag_tool.tool.color
    viewer.drag_tool.tool.visible = True
    viewer.drag_tool.tool.shape = shape
    yield

    # on mouse move
    while event.type == "mouse_move":
        viewer.drag_tool.tool.color = ACTIVE_COLOR if event.modifiers else color
        yield

    # on release
    viewer.drag_tool.tool.color = color
    viewer.drag_tool.tool.visible = False
    position = _get_span_position(shape, viewer.drag_tool.tool.position, view_rect)
    viewer.drag_tool.tool.position = (0, 0, 0, 0)
    _set_modifier_range(viewer, event.modifiers, position)
    viewer.events.span(position=position)


box_zoom_vert = partial(box_zoom_shape, Shape.VERTICAL)
box_zoom_horz = partial(box_zoom_shape, Shape.HORIZONTAL)
box_zoom_box = partial(box_zoom_shape, Shape.BOX)
