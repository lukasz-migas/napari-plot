"""Camera model"""

from __future__ import annotations

import typing as ty

from napari._pydantic_compat import validator
from napari.utils.compat import StrEnum
from napari.utils.events import Event, EventedModel
from napari.utils.misc import ensure_n_tuple


class CameraMode(StrEnum):
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


class ExtentMode(StrEnum):
    """Mode specifying whether plot extents should be specified."""

    RESTRICTED = "restricted"
    UNRESTRICTED = "unrestricted"


EXTENT_MODE_TRANSLATIONS = {
    ExtentMode.RESTRICTED: "restricted",
    ExtentMode.UNRESTRICTED: "unrestricted",
}


class Camera(EventedModel):
    """Camera object modeling position and view of the camera.

    Attributes
    ----------
    mouse_pan : bool
        If the camera interactive panning with the mouse is enabled or not.
    mouse_zoom : bool
        If the camera interactive zooming with the mouse is enabled or not.
    zoom : float
        Scale from canvas pixels to world pixels. This variable is not used in napari-plot but is kept for compatibility
        with napari.
    rect : 4-tuple
        The Left, right, top and bottom corners the camera should be set to.
    extent : 4-tuple
        The Left, right, top and bottom corner limits the camera should restrict the view to. This value is only used to
        restrict the view to specified x/y-axis range and will limit the allowable zoom range when the
        ExtentMode.RESTRICTED mode is set. See below for more information.
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
    mouse_pan: bool = True
    mouse_zoom: bool = True
    aspect: ty.Optional[float] = None
    zoom: float = 1.0
    rect: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    extent: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    x_range: ty.Optional[tuple[float, float]] = None
    y_range: ty.Optional[tuple[float, float]] = None
    extent_mode: ExtentMode = ExtentMode.UNRESTRICTED
    axis_mode: tuple[CameraMode, ...] = (CameraMode.ALL,)

    # private field
    # this attribute is quite special and must be set alongside `extent` but only if e.g. layer is being added as it
    # is used as a backup for resetting x/y-axis ranges.
    _extent: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.events.add(force_rect=Event, zoomed=Event)

    # validators
    @validator("x_range", "y_range", pre=True)
    def _ensure_2_tuple(cls, v) -> ty.Optional[tuple[float, float]]:
        if v is None:
            return v
        return ensure_n_tuple(v, n=2)

    @validator("rect", "extent", pre=True)
    def _ensure_4_tuple(cls, v) -> tuple[float, float, float, float]:
        return ensure_n_tuple(v, n=4)

    @validator("axis_mode", pre=True)
    def _ensure_axis_tuple(cls, v: ty.Union[CameraMode, tuple[CameraMode]]) -> tuple[CameraMode]:
        if not isinstance(v, tuple):
            return (v,)
        return tuple(v)

    def set_rect(self, xmin, xmax, ymin, ymax):
        """Set the camera rectangle."""
        self.rect = (xmin, xmax, ymin, ymax)
        # self.events.force_rect()

    def get_effective_extent(self) -> tuple[float, float, float, float]:
        """This function returns extent based on current values of `x_range` and `y_range`."""
        x0, x1, y0, y1 = self._extent
        if self.x_range is not None:
            x0, x1 = self.x_range
        if self.y_range is not None:
            y0, y1 = self.y_range
        return x0, x1, y0, y1

    def set_x_range(self, min_val: ty.Optional[float] = None, max_val: ty.Optional[float] = None):
        """Set x-axis range."""
        if min_val is None and max_val is None:
            self.x_range = None
        else:
            x0, x1, _, _ = self._extent
            self.x_range = (
                min_val if min_val is not None else x0,
                max_val if max_val is not None else x1,
            )

    def set_y_range(self, min_val: ty.Optional[float] = None, max_val: ty.Optional[float] = None):
        """Set y-axis range."""
        if min_val is None and max_val is None:
            self.y_range = None
        else:
            _, _, y0, y1 = self._extent
            self.y_range = (
                min_val if min_val is not None else y0,
                max_val if max_val is not None else y1,
            )
