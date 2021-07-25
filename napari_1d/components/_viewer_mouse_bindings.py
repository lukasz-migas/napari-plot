"""Mouse bindings to the viewer"""


def x_span(viewer, event):
    """Enable x-axis span."""

    def _is_not_modifier() -> bool:
        return "Control" not in event.modifiers and "Shift" not in event.modifiers

    if _is_not_modifier() or event.button != 1:
        viewer.span.visible = False
        return

    if not viewer.span.visible:
        viewer.span.visible = True

    # on mouse press
    color = viewer.span.color
    viewer.span.color = (1.0, 0.0, 0.0, 1.0)
    yield

    # on mouse move
    while event.type == "mouse_move":
        viewer.span.visible = not _is_not_modifier()
        yield

    # on release
    viewer.span.color = color
    if not _is_not_modifier():
        position = viewer.span.position
        viewer.span.visible = False
        viewer.span.position = (0, 0)
        viewer.events.span(position=position)
    yield
