"""Camera model"""
import typing as ty
from enum import Enum

from napari.utils.events import EventedModel
from napari.utils.misc import ensure_n_tuple
from pydantic import validator


class CameraMode(str, Enum):
    """Interaction mode

    Sets the zoom mode:
        * all: no locking available
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
        Scale from canvas pixels to world pixels. This variable is not used in napari-plot but is kept for compatibility
        with napari.
    rect : 4-tuple
        The Left, right, top and bottom corners the camera should be set to.
    extent : 4-tuple
        The Left, right, top and bottom corner limits the camera should restrict the view to. See `restrict` value
        for the available modes.
    extent_mode : ExtentMode
        Specify whether the plot limits should be restricted using the `extent` value or not.
        ExtentMode.RESTRICTED
            The value of `extent` will be automatically set and plot will always be limited to the available area.
        ExtentMode.UNRESTRICTED
            The value of `extent` will NOT be used and zooming out will be permitted to outside of the plot area.
    axis_mode : tuple of CameraMode
        Specify the x/y-axis behaviour during normal interaction.
        CameraMode.ALL
            There will be no restrictions in the way the camera zooms in and out.
        CameraMode.LOCK_TO_BOTTOM
            The lower y-axis value will be locked so it does not zoom-out further than the lowest possible value.
        CameraMode.LOCK_TO_TOP
            The upper y-axis value will be locked so it does not zoom-out further than the highest possible value.
        CameraMode.LOCK_TO_LEFT
            The lower x-axis value will be locked so it does not zoom-out further than the lowest possible value.
        CameraMode.LOCK_TO_RIGHT
            The upper x-axis value will be locked so it does not zoom-out further than the highest possible value.
    """

    # fields
    interactive: bool = True
    zoom: float = 1.0
    rect: ty.Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    extent: ty.Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    x_range: ty.Optional[ty.Tuple[float, float]] = None
    y_range: ty.Optional[ty.Tuple[float, float]] = None
    extent_mode: ExtentMode = ExtentMode.UNRESTRICTED
    axis_mode: ty.Tuple[CameraMode, ...] = (CameraMode.ALL,)

    # validators
    @validator("x_range", "y_range", pre=True)
    def _ensure_2_tuple(v) -> ty.Optional[ty.Tuple[float, float]]:
        if v is None:
            return v
        return ensure_n_tuple(v, n=2)

    @validator("rect", "extent", pre=True)
    def _ensure_4_tuple(v) -> ty.Tuple[float, float, float, float]:
        return ensure_n_tuple(v, n=4)

    @validator("axis_mode", pre=True)
    def _ensure_axis_tuple(v: ty.Union[CameraMode, ty.Tuple[CameraMode]]) -> ty.Tuple[CameraMode]:
        if not isinstance(v, tuple):
            return (v,)
        return tuple(v)
