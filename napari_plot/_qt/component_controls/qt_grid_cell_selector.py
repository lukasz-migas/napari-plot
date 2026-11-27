"""Selector of the grid cell that a settings dialog edits."""

from __future__ import annotations

from typing import TYPE_CHECKING
from weakref import ref

import qtextra.helpers as hp
from napari._qt.utils import qt_signals_blocked
from napari.utils.events import disconnect_events
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QWidget

from napari_plot.layers._grouping import get_layer_group

if TYPE_CHECKING:
    from collections.abc import Callable

    from napari.layers import Layer
    from napari.utils.events import EmitterGroup, Event

    from napari_plot.components.viewer_model import ViewerModel

GridTarget = tuple[int, int] | None

# layer-list events that can move layers between grid cells or change how a cell is named
_LAYOUT_EVENTS = frozenset({"inserted", "removed", "reordered", "moved", "changed", "visible", "name", "metadata"})
_MAX_TITLE = 48


def connect_all(events: EmitterGroup, callback: Callable[..., None]) -> None:
    """Connect ``callback`` to every emitter of ``events``, so ``disconnect_events`` can remove it again."""
    for emitter in events.emitters.values():
        emitter.connect(callback)


def cell_title(row: int, col: int, layers: list[Layer]) -> str:
    """Return the selector text of a grid cell: its position and group name or layer names."""
    groups = {get_layer_group(layer) for layer in layers} - {None}
    content = next(iter(groups)) if len(groups) == 1 else ", ".join(layer.name for layer in layers)
    title = f"Cell {row + 1}, {col + 1}" + (f" - {content}" if content else "")
    return title if len(title) <= _MAX_TITLE else title[: _MAX_TITLE - 3] + "..."


class QtGridCellSelector(QWidget):
    """Choose whether a settings widget edits all cells (the global settings) or one cell of a regular grid.

    The selector is hidden when the grid is off and disabled in joint mode. It rebuilds when the grid layout changes
    and falls back to all cells when the selected cell disappears. ``target_changed`` emits ``None`` (all cells) or
    the ``(row, column)`` of the selected cell.
    """

    target_changed = Signal(object)

    def __init__(self, viewer: ViewerModel, parent: QWidget | None = None, target: GridTarget = None) -> None:
        super().__init__(parent)
        self.ref_viewer = ref(viewer)
        self.combobox = hp.make_combobox(self, tooltip="Edit the settings of all cells, or of one cell of the grid.")
        self.combobox.currentIndexChanged.connect(self._on_index_changed)
        hp.make_h_layout(
            hp.make_label(self, "Target"), self.combobox, stretch_id=(1,), spacing=4, margin=0, parent=self
        )
        connect_all(viewer.canvas.grid.events, self._refresh)
        viewer.layers.events.connect(self._on_layers_event)
        self._refresh()
        if target is not None:
            self.set_target(target)

    @property
    def target(self) -> GridTarget:
        """The selected cell as ``(row, column)``, or ``None`` for all cells."""
        return self.combobox.currentData()

    def set_target(self, target: GridTarget) -> None:
        """Select a cell (``None`` selects all cells); a cell that is not shown selects all cells."""
        index = self._index_of(target)
        self.combobox.setCurrentIndex(0 if index < 0 else index)

    def _index_of(self, target: GridTarget) -> int:
        return next((index for index in range(self.combobox.count()) if self.combobox.itemData(index) == target), -1)

    def _on_index_changed(self, _index: int) -> None:
        self.target_changed.emit(self.target)

    def _on_layers_event(self, event: Event) -> None:
        if event.type in _LAYOUT_EVENTS:
            self._refresh()

    def _refresh(self, _event: Event | None = None) -> None:
        """List the cells of the current grid layout, keeping the selection when the cell is still shown."""
        viewer = self.ref_viewer()
        if viewer is None:
            return
        grid = viewer.canvas.grid
        previous = self.target
        with qt_signals_blocked(self.combobox):
            self.combobox.clear()
            self.combobox.addItem("All cells (global)", None)
            for (row, col), layers in sorted(viewer._grid_cells().items()):
                self.combobox.addItem(cell_title(row, col, layers), (row, col))
            index = self._index_of(previous)
            self.combobox.setCurrentIndex(max(index, 0))
        self.setVisible(grid.enabled)
        self.setEnabled(not grid.joint)
        self.setToolTip("Per-cell settings are not available in joint mode." if grid.joint else "")
        if index < 0:
            self.target_changed.emit(None)

    def disconnect_viewer(self) -> None:
        """Stop following the viewer's grid and layers."""
        viewer = self.ref_viewer()
        if viewer is not None:
            disconnect_events(viewer.canvas.grid.events, self)
            viewer.layers.events.disconnect(self._on_layers_event)
