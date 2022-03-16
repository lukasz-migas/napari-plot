"""Specialized camera for 1d data"""
import typing as ty

import numpy as np
from vispy.geometry import Rect
from vispy.scene import BaseCamera, PanZoomCamera

from ...components.camera import CameraMode, ExtentMode
from ...components.dragtool import BOX_ZOOM_TOOLS
from ...components.tools import Shape

if ty.TYPE_CHECKING:
    from ...components.viewer_model import ViewerModel


def make_rect(xmin: float, xmax: float, ymin: float, ymax: float) -> Rect:
    """Make rect."""
    rect = Rect()
    rect.left, rect.right, rect.bottom, rect.top = xmin, xmax, ymin, ymax
    return rect


class LimitedPanZoomCamera(PanZoomCamera):
    """Slightly customized pan zoom camera that prevents zooming outside of specified region"""

    _extent = None
    _axis_mode: ty.Tuple[CameraMode, ...] = (CameraMode.ALL,)
    _extent_mode: ExtentMode = ExtentMode.UNRESTRICTED

    def __init__(self, viewer: "ViewerModel", *args, **kwargs):
        self.viewer = viewer
        super().__init__(*args, **kwargs)

    @property
    def axis_mode(self) -> ty.Tuple[CameraMode, ...]:
        """Return axis mode."""
        return self._axis_mode

    @axis_mode.setter
    def axis_mode(self, value: ty.Tuple[CameraMode, ...]):
        self._axis_mode = value

    @property
    def extent_mode(self):
        """Return extent mode."""
        return self._extent_mode

    @extent_mode.setter
    def extent_mode(self, value: ExtentMode):
        self._extent_mode = value
        self._extent = None
        self._default_state["rect"] = None

    @property
    def extent(self) -> ty.Tuple[float, float, float, float]:
        """Return extent values."""
        return self._extent

    @extent.setter
    def extent(self, extent: ty.Tuple[float, float, float, float]):
        rect = Rect()
        rect.left, rect.right, rect.bottom, rect.top = extent
        self._extent = rect
        self._default_state["rect"] = rect

    def reset_view(self):
        """Reset view."""
        self.rect = self.extent

    def viewbox_mouse_event(self, event):
        """
        The SubScene received a mouse event; update transform
        accordingly.

        Parameters
        ----------
        event : instance of Event
            The event.
        """
        if event.handled or not self.interactive:
            return

        # Scrolling
        BaseCamera.viewbox_mouse_event(self, event)

        if event.type == "mouse_wheel":
            center = self._scene_transform.imap(event.pos)
            self.zoom((1 + self.zoom_factor) ** (-event.delta[1] * 30), center)
            event.handled = True

        elif event.type == "mouse_move":
            if event.press_event is None:
                return

            modifiers = event.mouse_event.modifiers
            # the left-button click on the mouse performs boxzoom (or whatever active tool is being used)
            if 1 in event.buttons:  # and not modifiers:
                x0, y0, _, _ = self._transform.imap(np.asarray(event.press_event.pos[:2]))
                x1, y1, _, _ = self._transform.imap(np.asarray(event.pos[:2]))
                x0, x1, y0, y1 = self._check_range(x0, x1, y0, y1)
                self.viewer.drag_tool.tool.position = x0, x1, y0, y1
                event.handled = True
            # the right-button click moves the canvas in x/y direction
            elif 2 in event.buttons and not modifiers:  # right-button click
                # Translate
                p1 = np.array(event.last_event.pos)[:2]
                p2 = np.array(event.pos)[:2]
                p1s = self._transform.imap(p1)
                p2s = self._transform.imap(p2)
                self.pan(p1s - p2s)
                event.handled = True
            else:
                event.handled = False
        elif event.type == "mouse_press":
            # accept the event if it is button 1 or 2.
            x1, y1, _, _ = self._transform.imap(np.asarray(event.pos[:2]))
            self.viewer.drag_tool.tool.position = x1, x1, y1, y1
            # This is required in order to receive future events
            event.handled = event.button in [1, 2]
        elif event.type == "mouse_release" and 1 in event.buttons:
            modifiers = event.mouse_event.modifiers
            x0, y0, _, _ = self._transform.imap(np.asarray(event.press_event.pos[:2]))
            x1, y1, _, _ = self._transform.imap(np.asarray(event.pos[:2]))
            # here we check that the different between values is not too small (might not work for plots with small
            # values?) and whether the user is using modifiers.
            if abs(x1 - x0) > 1e-3 and not (self.viewer.drag_tool.selecting and modifiers):
                # this call makes sure that various axis/extent checks are performed
                x0, x1, y0, y1 = self._check_range(x0, x1, y0, y1)
                rect = self._make_zoom_rect(x0, x1, y0, y1)
                if rect:
                    self.rect = rect
        else:
            event.handled = False

    def _make_zoom_rect(self, x0: float, x1: float, y0: float, y1: float) -> Rect:
        """Make zoom rectangle based on the currently active tool."""
        # I don't like this because it adds dependency on a instance of the viewer, however, here we can check
        # what is the most appropriate y-axis range for line plots.
        x0, x1, y0, y1 = self._check_range(x0, x1, y0, y1)
        extent = self.extent
        last = self.rect
        if self.viewer.drag_tool.active in BOX_ZOOM_TOOLS:
            if self.viewer.drag_tool.tool.shape == Shape.VERTICAL:
                # x0, x1 = self.viewer._get_x_range_extent_for_y(y0, y1)
                if last is not None:
                    y0, y1 = last.bottom, last.top
                elif extent is not None:
                    y0, y1 = extent.bottom, extent.top
            elif self.viewer.drag_tool.tool.shape == Shape.HORIZONTAL:
                if last is not None:
                    x0, x1 = last.left, last.right
                elif extent is not None:
                    x0, x1 = extent.left, extent.right
            return make_rect(x0, x1, y0, y1)

    def _check_zoom_limit(self, rect: Rect) -> Rect:
        """Check whether new range is outside of the allowed window"""
        rect.left, rect.right, rect.bottom, rect.top = self._check_range(rect.left, rect.right, rect.bottom, rect.top)
        return rect

    def _check_mode_limit(self, rect: Rect) -> Rect:
        """Check whether there are any restrictions on the movement"""
        axis_mode = self.axis_mode
        limit_rect = self.extent
        # no locking mechanism is enabled or extens have not been set yet
        if CameraMode.ALL in axis_mode or limit_rect is None:
            return rect
        if CameraMode.LOCK_TO_BOTTOM in axis_mode:
            rect.bottom = limit_rect.bottom
        if CameraMode.LOCK_TO_TOP in axis_mode:
            rect.top = limit_rect.top
        if CameraMode.LOCK_TO_LEFT in axis_mode:
            rect.left = limit_rect.left
        if CameraMode.LOCK_TO_RIGHT in axis_mode:
            rect.right = limit_rect.right
        return rect

    def _check_range(self, x0: float, x1: float, y0: float, y1: float) -> ty.Tuple[float, float, float, float]:
        """Check whether values are correct"""
        # check whether values are in correct order (low, high)
        if y1 < y0:
            y0, y1 = y1, y0
        if x1 < x0:
            x0, x1 = x1, x0

        # check whether extent values are set and if so, limit the values
        if self.extent_mode == ExtentMode.RESTRICTED and self.extent is not None:
            limit_rect = self.extent
            if x0 < limit_rect.left:
                x0 = limit_rect.left
            if x1 > limit_rect.right:
                x1 = limit_rect.right
            if y0 < limit_rect.bottom:
                y0 = limit_rect.bottom
            if y1 > limit_rect.top:
                y1 = limit_rect.top
        return x0, x1, y0, y1

    @property
    def rect(self) -> Rect:
        """Get rect"""
        return super().rect

    @rect.setter
    def rect(self, args):
        if isinstance(args, tuple):
            rect = Rect(*args)
        else:
            rect = Rect(args)

        # ensure user never goes outside of allowed limits
        rect = self._check_zoom_limit(rect)
        rect = self._check_mode_limit(rect)

        if self._rect != rect:
            self._rect = rect
            self.view_changed()
