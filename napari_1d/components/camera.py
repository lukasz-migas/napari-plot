"""Camera model"""
# Standard library imports
import typing as ty
from enum import Enum

# Third-party imports
from napari.utils.events import EventedModel
from napari.utils.misc import ensure_n_tuple
from pydantic import validator


class CameraMode(str, Enum):
    """Interaction mode

    Sets the zoom mode:
        * all: no locking available
        * bottom_zero: bottom axis is always 0
        * lock_to_bottom: the axis zoom will be locked at the bottom of the canvas
        * lock_to_top: the axis zoom
        * lock_to_left:
        * lock_to_right:
    """

    ALL = "all"
    LOCK_TO_BOTTOM = "lock_to_bottom"
    LOCK_TO_TOP = "lock_to_top"
    LOCK_TO_LEFT = "lock_to_left"
    LOCK_TO_RIGHT = "lock_to_right"


class ExtentMode(str, Enum):
    """Mode specifying whether plot extents should be specified."""

    RESTRICTED = "restricted"
    UNRESTRICTED = "unrestricted"


class Camera(EventedModel):
    """Camera object modeling position and view of the camera.

    Attributes
    ----------
    interactive : bool
        If the camera interactivity is enabled or not.
    zoom : float
        Scale from canvas pixels to world pixels. This variable is not used in napari-1d but is kept for compatibility
        with napari.
    rect : 4-tuple
        The Left, right, top and bottom corners the camera should be set to.
    extent : 4-tuple
        The Left, right, top and bottom corner limits the camera should restrict the view to. See `restrict` value
        for the available modes.
    restrict : ExtentMode
        Specify whether the plot limits should be restricted using the `extent` value of not.
        ExtentMode.RESTRICTED
            The value of `extent` will be automatically set and plot will always be limited to the available area.
        ExtentMode.UNRESTRICTED
            The value of `extent` will NOT be used and zooming out will be permitted to outside of the plot area.
    mode : CameraMode
        Specify the x/y-axis behaviour during normal interaction.
    """

    # fields
    interactive: bool = True
    zoom: float = 1.0
    rect: ty.Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    extent_mode: ExtentMode = ExtentMode.UNRESTRICTED
    extent: ty.Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    axis_mode: ty.Tuple[CameraMode] = (CameraMode.ALL,)

    # validators
    @validator("rect", "extent", pre=True)
    def _ensure_r_tuple(v) -> ty.Tuple[float, float, float, float]:
        return ensure_n_tuple(v, n=4)

    @validator("axis_mode", pre=True)
    def _ensure_axis_tuple(v: ty.Union[CameraMode, ty.Tuple[CameraMode]]) -> ty.Tuple[CameraMode]:
        if not isinstance(v, tuple):
            return (v,)
        return v
