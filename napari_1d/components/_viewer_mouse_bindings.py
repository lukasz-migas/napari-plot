"""Mouse bindings to the viewer"""
from .tools import Shape

ACTIVE_COLOR = (1.0, 0.0, 0.0, 1.0)


def boxzoom(viewer, event):
    """Enable box zoom."""

    def _get_shape():
        if "Control" in event.modifiers:
            return Shape.VERTICAL
        elif "Shift" in event.modifiers:
            return Shape.HORIZONTAL
        return Shape.BOX

    # make sure box is visible
    if not viewer.drag_tool.tool.visible:
        viewer.drag_tool.tool.visible = True

    # on press
    color = viewer.drag_tool.tool.color
    viewer.drag_tool.tool.shape = _get_shape()
    yield

    # on mouse move
    while event.type == "mouse_move":
        viewer.drag_tool.tool.shape = _get_shape()
        yield

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
