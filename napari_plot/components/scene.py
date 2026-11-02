"""Scene model for the plot's two-dimensional camera."""

from napari.utils.events import EventedModel
from pydantic import Field

from napari_plot.components.camera import Camera


class Scene(EventedModel):
    """Own the plotting camera without introducing napari's 3D camera."""

    camera: Camera = Field(default_factory=Camera, frozen=True)
