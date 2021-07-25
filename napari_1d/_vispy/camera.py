"""Specialized camera for 1d data"""
from typing import TYPE_CHECKING

# Third-party imports
import numpy as np
from vispy.geometry import Rect
from vispy.scene import BaseCamera, PanZoomCamera
from vispy.util.event import Event

# Local imports
from ..components.camera import Mode

if TYPE_CHECKING:
    from ..components.viewer_model import ViewerModel


def make_rect(xmin, xmax, ymin, ymax):
    """Make rect."""
    rect = Rect()
    rect.left = xmin
    rect.right = xmax
    rect.bottom = ymin
    rect.top = ymax
    return rect


class LimitedPanZoomCamera(PanZoomCamera):
    """Slightly customized pan zoom camera that prevents zooming outside of specified region"""

    _extents = None
    _mode: Mode = Mode.BOTTOM_ZERO

    def __init__(self, viewer: "ViewerModel", *args, **kwargs):
        self.viewer = viewer
        super().__init__(*args, **kwargs)

        self.events.add(box_move=Event, box_press=Event)

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

            # By default, the left-mouse pans the plot but it actually should be a box-zoom
            if 1 in event.buttons:  # and not modifiers:
                x0, y0, _, _ = self._transform.imap(np.asarray(event.press_event.pos[:2]))
                x1, y1, _, _ = self._transform.imap(np.asarray(event.pos[:2]))
                x0, x1, y0, y1 = self._check_range(x0, x1, y0, y1)
                self.events.box_move(rect=(x0, x1, y0, y1))
                event.handled = True
            elif 2 in event.buttons and not modifiers:
                # Zoom
                p1c = np.array(event.last_event.pos)[:2]
                p2c = np.array(event.pos)[:2]
                scale = (1 + self.zoom_factor) ** ((p1c - p2c) * np.array([1, -1]))
                center = self._transform.imap(event.press_event.pos[:2])
                self.zoom(scale, center)
                event.handled = True
            else:
                event.handled = False
        elif event.type == "mouse_press":
            # accept the event if it is button 1 or 2.
            # This is required in order to receive future events
            event.handled = event.button in [1, 2]
            self.events.box_press(visible=True)
        elif event.type == "mouse_release":
            # this is where we change the interaction and actually perform various checks to ensure user doesn't zoom
            # to someplace where they shouldn't
            modifiers = event.mouse_event.modifiers
            x0, y0, _, _ = self._transform.imap(np.asarray(event.press_event.pos[:2]))
            x1, y1, _, _ = self._transform.imap(np.asarray(event.pos[:2]))
            # ensure that user selected broad enough range and they are not using ctrl/shift modifiers
            if abs(x1 - x0) > 1e-3 and not modifiers:
                x0, x1, y0, y1 = self._check_range(x0, x1, y0, y1)
                # I don't like this because it adds dependency on a instance of the viewer, however, here we can check
                # what is the most appropriate y-axis range for line plots.
                y0, y1 = self.viewer._get_y_range_extent_for_x(x0, x1)
                self.rect = make_rect(x0, x1, y0, y1)
            self.events.box_press(visible=False)
        else:
            event.handled = False

    def set_mode(self, mode: Mode):
        """Set limit mode."""
        self._mode = mode

    def set_extents(self, xmin, xmax, ymin, ymax):
        """Set plot extents"""
        rect = Rect()
        rect.left = xmin
        rect.right = xmax
        rect.bottom = ymin
        rect.top = ymax
        self._extents = rect
        self._default_state["rect"] = rect

    def _check_zoom_limit(self, rect: Rect):
        """Check whether new range is outside of the allowed window"""
        if isinstance(rect, Rect) and self._extents is not None:
            limit_rect = self._extents
            if rect.left < limit_rect.left:
                rect.left = limit_rect.left
            if rect.right > limit_rect.right:
                rect.right = limit_rect.right
            if rect.bottom < limit_rect.bottom:
                rect.bottom = limit_rect.bottom
            if rect.top > limit_rect.top:
                rect.top = limit_rect.top
        return rect

    def _check_mode_limit(self, rect: Rect) -> Rect:
        """Check whether there are any restrictions on the movement"""
        if self._mode == Mode.ALL or self._extents is None:
            return rect
        elif self._mode == Mode.BOTTOM_ZERO:
            rect.bottom = np.min([0, rect.bottom])
        elif self._mode == Mode.LOCK_TO_BOTTOM:
            rect.bottom = self._extents.bottom
        elif self._mode == Mode.LOCK_TO_TOP:
            rect.top = self._extents.top
        elif self._mode == Mode.LOCK_TO_LEFT:
            rect.left = self._extents.left
        elif self._mode == Mode.LOCK_TO_RIGHT:
            rect.right = self._extents.right
        return rect

    def _check_range(self, x0, x1, y0, y1):
        """Check whether values are correct"""
        if y1 < y0:
            y0, y1 = y1, y0
        if x1 < x0:
            x0, x1 = x1, x0
        if self._extents is not None:
            limit_rect = self._extents
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
    def rect(self):
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
