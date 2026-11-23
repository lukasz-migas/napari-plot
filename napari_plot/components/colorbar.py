"""Colorbar drawn next to the plot."""

from __future__ import annotations

import typing as ty

from napari.utils.colormaps import Colormap, ensure_colormap
from napari.utils.events import EventedModel
from pydantic import Field, field_validator


class ColorBar(EventedModel):
    """Color scale shown at the right or bottom edge of a plot.

    Attributes
    ----------
    visible : bool
        Whether the colorbar is shown. The plot gives up the space it needs only while it is visible.
    colormap : Colormap
        Colormap of the bar; any value accepted by napari's ``ensure_colormap``.
    contrast_limits : tuple of float
        Lowest and highest values shown on the bar.
    label : str
        Text drawn along the bar, outside its tick labels.
    bar_width : int
        Thickness of the color gradient in screen pixels.
    norm : {"linear", "log"}
        Scale used to space the ticks. Log spacing applies to positive limits.
    """

    visible: bool = False
    colormap: Colormap = Field(default_factory=lambda: ensure_colormap("viridis"))
    contrast_limits: tuple[float, float] = (0.0, 1.0)
    label: str = ""
    bar_width: int = Field(15, gt=0)
    position: ty.Literal["right", "bottom"] = "right"
    norm: ty.Literal["linear", "log"] = "linear"
    gamma: float = Field(1.0, gt=0)

    @property
    def orientation(self) -> ty.Literal["vertical", "horizontal"]:
        """Return the orientation implied by the edge placement."""
        return "vertical" if self.position == "right" else "horizontal"

    @orientation.setter
    def orientation(self, value: ty.Literal["vertical", "horizontal"]) -> None:
        if value not in ("vertical", "horizontal"):
            raise ValueError("Colorbar orientation must be vertical or horizontal.")
        self.position = "right" if value == "vertical" else "bottom"

    @field_validator("colormap", mode="before")
    @classmethod
    def _coerce_colormap(cls, value: ty.Any) -> Colormap:
        return ensure_colormap(value)
