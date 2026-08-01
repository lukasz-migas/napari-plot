"""Compound visual used by the Text layer."""

from __future__ import annotations

from typing import Any

from vispy.scene.visuals import Compound, Text as VispyText


class TextVisual(Compound):
    """A dynamically grouped collection of VisPy text visuals."""

    def __init__(self) -> None:
        self._base_sizes: list[float] = []
        super().__init__([])

    def set_groups(
        self,
        groups: list[dict[str, Any]],
        *,
        face: str,
        bold: bool,
        italic: bool,
        font_manager: Any,
        scale_factor: float,
        scaling: bool,
    ) -> None:
        """Replace the text subvisuals with the supplied style groups."""
        for visual in tuple(self._subvisuals):
            self.remove_subvisual(visual)
        self._base_sizes = [float(group["size"]) for group in groups]

        for group in groups:
            self.add_subvisual(
                VispyText(
                    text=group["text"],
                    pos=group["pos"],
                    color=group["color"],
                    font_size=self._scaled_size(
                        group["size"],
                        scale_factor=scale_factor,
                        scaling=scaling,
                    ),
                    rotation=group["rotation"],
                    anchor_x=group["alignment"],
                    anchor_y=group["vertical_alignment"],
                    face=face,
                    bold=bold,
                    italic=italic,
                    font_manager=font_manager,
                )
            )
        self.update()

    @staticmethod
    def _scaled_size(size: float, *, scale_factor: float, scaling: bool) -> float:
        """Return a screen-space font size for the current zoom scale."""
        return float(size) / scale_factor if scaling else float(size)

    def update_scale(self, *, scale_factor: float, scaling: bool) -> None:
        """Update font sizes without rebuilding text groups."""
        for visual, size in zip(self._subvisuals, self._base_sizes, strict=True):
            visual.font_size = self._scaled_size(
                size,
                scale_factor=scale_factor,
                scaling=scaling,
            )
        self.update()


__all__ = ["TextVisual"]
