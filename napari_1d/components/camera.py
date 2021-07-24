"""Camera model"""
# Standard library imports
from enum import Enum
from typing import Tuple

# Third-party imports
from napari.utils.events import EventedModel
from napari.utils.misc import ensure_n_tuple
from pydantic import validator


class Mode(str, Enum):
    """Interaction mode

    Sets the zoom mode:
        * all: no locking available
        * bottom_zero: bottom axis is always 0
        * lock_to_bottom: the axis zoom will be locked at the bottom of the canvas
        * lock_to_top:
        * lock_to_left:
        * lock_to_right:
    """

    ALL = "all"
    BOTTOM_ZERO = "bottom_zero"
    LOCK_TO_BOTTOM = "lock_to_bottom"
    LOCK_TO_TOP = "lock_to_top"
    LOCK_TO_LEFT = "lock_to_left"
    LOCK_TO_RIGHT = "lock_to_right"


class Camera(EventedModel):
    """Camera object modeling position and view of the camera.

    Attributes
    ----------
    rect : 4-tuple
        The Left, right, top and bottom corners the camera should be set to.
    zoom : float
        Scale from canvas pixels to world pixels.
    interactive : bool
        If the camera interactivity is enabled or not.
    """

    # fields
    rect: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    extent: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    zoom: float = 1.0
    interactive: bool = True
    mode: Mode = Mode.ALL

    # validators
    @validator("rect", "extent", pre=True)
    def _ensure_r_tuple(v):
        return ensure_n_tuple(v, n=4)
