"""Mouse bindings to the viewer"""
from .box import Shape


def boxzoom(viewer, event):
    """Enable box zoom."""

    def _get_shape():
        if "Control" in event.modifiers:
            return Shape.VERTICAL
        elif "Shift" in event.modifiers:
            return Shape.HORIZONTAL
        return Shape.BOX

    # make sure box is visible
    if not viewer.box_tool.visible:
        viewer.box_tool.visible = True

    # on mouse press
    color = viewer.box_tool.color
    viewer.box_tool.shape = _get_shape()
    yield

    # on mouse move
    while event.type == "mouse_move":
        viewer.box_tool.shape = _get_shape()
        yield

    # on release
    viewer.box_tool.color = color
    position = viewer.box_tool.position
    viewer.box_tool.visible = False
    viewer.box_tool.position = (0, 0, 0, 0)
    viewer.events.span(position=position)
    yield
