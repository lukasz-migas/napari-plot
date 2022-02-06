"""Mouse bindings to the viewer"""
from functools import partial

from .tools import Shape

ACTIVE_COLOR = (1.0, 0.0, 0.0, 1.0)


def boxzoom(viewer, event):
    """Enable box zoom."""

    def _get_shape():
        if sx0 is None or "Alt" in event.modifiers:
            return Shape.BOX
        x0, x1, y0, y1 = viewer.drag_tool.tool.position
        x, y = abs(x1 - x0), abs(y1 - y0)
        # if there is minimum difference in y-position, lets show it as vertical span
        if y < ey:
            return Shape.VERTICAL
        # if there is minimum difference in x-position, lets show it as horizontal span
        elif x < ex:
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
