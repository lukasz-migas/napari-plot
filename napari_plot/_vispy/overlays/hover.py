"""Hover readout visual."""

from __future__ import annotations

import typing as ty

from napari_plot._vispy.overlays.text import VispyTextOverlay

if ty.TYPE_CHECKING:
    from napari.utils.events import Event


class VispyHoverOverlay(VispyTextOverlay):
    """Text box of the hover readout; hidden while no data is under the cursor."""

    def __init__(self, **kwargs: ty.Any) -> None:
        super().__init__(**kwargs)
        self.overlay.events.box_padding.connect(self._on_box_padding_change)
        self._on_box_padding_change()

    def _on_box_padding_change(self, _event: Event | None = None) -> None:
        self.box_padding = self.overlay.box_padding

    def _should_be_visible(self) -> bool:
        return self.overlay.visible and bool(self.overlay.text)

    def _on_text_change(self) -> None:
        super()._on_text_change()
        self.node.visible = self._should_be_visible()
        self._on_box_change()

    def close(self) -> None:
        """Disconnect the padding and close the visual."""
        self.overlay.events.box_padding.disconnect(self._on_box_padding_change)
        super().close()
