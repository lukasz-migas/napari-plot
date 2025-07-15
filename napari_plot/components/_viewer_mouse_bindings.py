"""Mouse bindings to the viewer"""

import typing as ty
from functools import partial

import numpy as np

from napari_plot.components.tools import Shape

if ty.TYPE_CHECKING:
    from napari_plot.viewer import Viewer

ACTIVE_COLOR: tuple = (1.0, 0.0, 0.0, 1.0)
EXTENT_MULTIPLIER: float = 0.10
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


def box_zoom_auto(viewer: "Viewer", event):
    """Enable box zoom."""

    def _get_shape():
        # handle modifiers first
        if "Alt" in event.modifiers or sx0 is None:
            return Shape.BOX
        if "Control" in event.modifiers:
            return Shape.VERTICAL
        if "Shift" in event.modifiers:
            return Shape.HORIZONTAL

        # then handle the shape
        x0, x1, y0, y1 = viewer.drag_tool.tool.position
        x, y = abs(x1 - x0), abs(y1 - y0)
        # if there is minimum difference in y-position, lets show it as vertical span
        if abs(sy - y) < ey:
            return Shape.VERTICAL
        # if there is minimum difference in x-position, lets show it as horizontal span
        if abs(sx - x) < ex:
            return Shape.HORIZONTAL
        return Shape.BOX

    # make sure box is visible
    if not viewer.camera.mouse_zoom or not viewer.camera.mouse_pan:
        return

    if not viewer.drag_tool.tool.visible:
        viewer.drag_tool.tool.visible = True

    # on press
    sx0, sx1, sy0, sy1 = None, None, None, None
    extent = viewer.camera.rect
    ex = abs(extent[1] - extent[0]) * EXTENT_MULTIPLIER
    ey = abs(extent[3] - extent[2]) * EXTENT_MULTIPLIER
    color = viewer.drag_tool.tool.color
    viewer.drag_tool.tool.shape = _get_shape()
    yield

    # on mouse move
    while event.type == "mouse_move":
        viewer.drag_tool.tool.shape = _get_shape()
        yield
        if sx0 is None:
            sx0, sx1, sy0, sy1 = viewer.drag_tool.tool.position
            sx, sy = abs(sx1 - sx0), abs(sy1 - sy0)

    # on release
    viewer.drag_tool.tool.color = color
    position = viewer.drag_tool.tool.position
    viewer.drag_tool.tool.visible = False
    viewer.drag_tool.tool.position = (0, 0, 0, 0)
    viewer.events.span(position=position)


def box_zoom_auto_trigger(viewer: "Viewer", event):
    """Enable box zoom."""

    def _get_shape():
        if sx0 is None:
            return Shape.BOX
        # then handle the shape
        x0, x1, y0, y1 = viewer.drag_tool.tool.position
        x, y = abs(x1 - x0), abs(y1 - y0)
        # if there is minimum difference in y-position, lets show it as vertical span
        if abs(sy - y) < ey:
            return Shape.VERTICAL
        # if there is minimum difference in x-position, lets show it as horizontal span
        if abs(sx - x) < ex:
            return Shape.HORIZONTAL
        return Shape.BOX

    def _set_event_range() -> bool:
        if not event.modifiers:
            return False
        if "Control" in event.modifiers:
            viewer.drag_tool.ctrl = position
        elif "Shift" in event.modifiers:
            viewer.drag_tool.shift = position
        elif "Alt" in event.modifiers:
            viewer.drag_tool.alt = position
        else:
            viewer.drag_tool.ctrl = (0, 0, 0, 0)
            viewer.drag_tool.shift = (0, 0, 0, 0)
            viewer.drag_tool.alt = (0, 0, 0, 0)
        return True

    # make sure box is visible
    if not viewer.camera.mouse_zoom or not viewer.camera.mouse_pan:
        return

    # on press
    sx0, sx1, sy0, sy1 = None, None, None, None
    extent = viewer.camera.rect
    ex = abs(extent[1] - extent[0]) * EXTENT_MULTIPLIER
    ey = abs(extent[3] - extent[2]) * EXTENT_MULTIPLIER
    color = viewer.drag_tool.tool.color
    viewer.drag_tool.tool.visible = True
    viewer.drag_tool.tool.shape = _get_shape()
    yield

    # on mouse move
    while event.type == "mouse_move":
        viewer.drag_tool.tool.shape = _get_shape()
        viewer.drag_tool.tool.color = ACTIVE_COLOR if event.modifiers else color
        yield
        if sx0 is None:
            sx0, sx1, sy0, sy1 = viewer.drag_tool.tool.position
            sx, sy = abs(sx1 - sx0), abs(sy1 - sy0)

    # on release
    viewer.drag_tool.tool.visible = False
    viewer.drag_tool.tool.color = color
    viewer.drag_tool.tool.position = (0, 0, 0, 0)
    viewer.drag_tool.selection_active = bool(event.modifiers)
    position = viewer.drag_tool.tool.position
    _set_event_range()
    viewer.events.span(position=position)


def box_zoom_shape(shape: Shape, viewer: "Viewer", event):
    """Enable box zoom."""

    def _set_event_range() -> bool:
        if not event.modifiers:
            return False
        if "Control" in event.modifiers:
            viewer.drag_tool.ctrl = position
        elif "Shift" in event.modifiers:
            viewer.drag_tool.shift = position
        elif "Alt" in event.modifiers:
            viewer.drag_tool.alt = position
        else:
            viewer.drag_tool.ctrl = (0, 0, 0, 0)
            viewer.drag_tool.shift = (0, 0, 0, 0)
            viewer.drag_tool.alt = (0, 0, 0, 0)
        return True

    # on press
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
    viewer.drag_tool.tool.position = (0, 0, 0, 0)
    position = viewer.drag_tool.tool.position
    _set_event_range()
    viewer.events.span(position=position)


box_zoom_vert = partial(box_zoom_shape, Shape.VERTICAL)
box_zoom_horz = partial(box_zoom_shape, Shape.HORIZONTAL)
box_zoom_box = partial(box_zoom_shape, Shape.BOX)
