"""Mouse bindings to the viewer"""
import typing as ty
from functools import partial

from .tools import Shape

if ty.TYPE_CHECKING:
    from ..viewer import Viewer

ACTIVE_COLOR = (1.0, 0.0, 0.0, 1.0)


def polygon(viewer: "Viewer", event):

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
    print(len(viewer.drag_tool.tool.data))
    viewer.drag_tool.vertices = viewer.drag_tool.tool.data


def lasso(viewer: "Viewer", event):

    """Enable polygon tool.

    This tool gives the user an option to draw a polygon in the canvas that will be used to select data in currently
    selected layer (or layers).

    The action is as follow:
        1. Left mouse click creates starting point.
        2. Left mouse drag keeps on adding points
        3. Right mouse click cancels lasso.
    """
    # on press
    if event.button == 1:  # left-click
        viewer.drag_tool.tool.add_point(event.position)
        viewer.drag_tool.tool.visible = True
    elif event.button == 2:  # right-click
        viewer.drag_tool.tool.clear()
        viewer.drag_tool.tool.visible = False
    yield

    # on mouse move
    while event.type == "mouse_move":
        if event.button == 1:
            viewer.drag_tool.tool.add_point(event.position)
        yield

    # on release
    viewer.drag_tool.vertices = viewer.drag_tool.tool.data


def boxzoom(viewer, event):
    """Enable box zoom."""

    def _get_shape():
        if sx0 is None or "Alt" in event.modifiers:
            return Shape.BOX
        x0, x1, y0, y1 = viewer.drag_tool.tool.position
        x, y = abs(x1 - x0), abs(y1 - y0)
        # if there is minimum difference in y-position, lets show it as vertical span
        if abs(sy - y) < ey:
            return Shape.VERTICAL
        # if there is minimum difference in x-position, lets show it as horizontal span
        elif abs(sx - x) < ex:
            return Shape.HORIZONTAL
        return Shape.BOX

    # make sure box is visible
    if not viewer.drag_tool.tool.visible:
        viewer.drag_tool.tool.visible = True

    # on press
    sx0, sx1, sy0, sy1 = None, None, None, None
    extent = viewer.camera.rect
    ex = abs(extent[1] - extent[0]) * 0.07
    ey = abs(extent[3] - extent[2]) * 0.07
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


def boxzoom_shape(shape: Shape, viewer, event):
    """Enable box zoom."""

    def _set_event_range():
        if "Control" in event.modifiers:
            viewer.drag_tool.ctrl = position
        elif "Shift" in event.modifiers:
            viewer.drag_tool.shift = position
        elif "Alt" in event.modifiers:
            viewer.drag_tool.alt = position

    # make sure box is visible
    if not viewer.drag_tool.tool.visible:
        viewer.drag_tool.tool.visible = True

    # on press
    color = viewer.drag_tool.tool.color
    viewer.drag_tool.tool.shape = shape
    yield

    # on mouse move
    while event.type == "mouse_move":
        if event.modifiers:
            viewer.drag_tool.tool.color = ACTIVE_COLOR
        else:
            viewer.drag_tool.tool.color = color
        yield

    # on release
    viewer.drag_tool.tool.color = color
    position = viewer.drag_tool.tool.position
    _set_event_range()
    viewer.drag_tool.tool.visible = False
    viewer.drag_tool.tool.position = (0, 0, 0, 0)
    viewer.events.span(position=position)


boxzoom_vertical = partial(boxzoom_shape, Shape.VERTICAL)
boxzoom_horizontal = partial(boxzoom_shape, Shape.HORIZONTAL)
boxzoom_box = partial(boxzoom_shape, Shape.BOX)
