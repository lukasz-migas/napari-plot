"""Colorbar drawn next to the plot."""

from __future__ import annotations

import typing as ty

from napari.utils.colormaps import Colormap, ensure_colormap
from napari.utils.events import EventedModel
from pydantic import Field, field_validator


class ColorBar(EventedModel):
    """Colorbar shown to the right of the plot, like a matplotlib colorbar.

    Attributes
    ----------
    visible : bool
        Whether the colorbar is shown. The plot gives up the space it needs only while it is visible.
    colormap : Colormap
        Colormap of the bar; any value accepted by napari's ``ensure_colormap``.
    contrast_limits : tuple of float
        Values at the bottom and top of the bar.
    label : str
        Text drawn along the bar, outside its tick labels.
    bar_width : int
        Width of the color gradient in screen pixels.
    """

    visible: bool = False
    colormap: Colormap = Field(default_factory=lambda: ensure_colormap("viridis"))
    contrast_limits: tuple[float, float] = (0.0, 1.0)
    label: str = ""
    bar_width: int = 15

    @field_validator("colormap", mode="before")
    @classmethod
    def _coerce_colormap(cls, value: ty.Any) -> Colormap:
        return ensure_colormap(value)
