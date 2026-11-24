"""Mouse bindings for editing scatter points."""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING

import numpy as np
from napari.layers.points._points_mouse_bindings import add as add_points, select as select_points

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from napari.utils.events import Event

    from napari_plot.layers.scatter.scatter import Scatter


def _edit_points(
    callback: Callable[[Scatter, Event], Generator[None, None, None]],
) -> Callable[[Scatter, Event], Generator[None, None, None]]:
    @wraps(callback)
    def edit(layer: Scatter, event: Event) -> Generator[None, None, None]:
        if event.button == 1 and not getattr(event, "plot_selection_tool", False):
            event.handled = True
            yield from callback(layer, event)

    return edit


add = _edit_points(add_points)


@_edit_points
def select(layer: Scatter, event: Event) -> Generator[None, None, None]:
    """Use napari's select gesture with center-based box selection for fixed markers."""
    if layer.scaling:
        yield from select_points(layer, event)
        return

    modify_selection = "Shift" in event.modifiers or "Control" in event.modifiers
    for _ in select_points(layer, event):
        yield
        if event.type == "mouse_release" and layer._is_selecting:
            box = layer._drag_box
            assert box is not None
            low, high = np.sort(box, axis=0)
            points = layer._view_data
            indices = layer._view_indices
            inside = np.all((points >= low) & (points <= high), axis=1) & layer.shown[indices]
            selection = set(indices[inside])
            if modify_selection:
                selection.symmetric_difference_update(layer.selected_data)
            # Skip napari's size-based box selection while keeping its release cleanup.
            layer._is_selecting = False
            layer.selected_data = selection
