"""Line-specific vispy canvas"""
from contextlib import contextmanager

from napari._vispy.utils.gl import get_max_texture_sizes
from qtpy.QtCore import QSize
from vispy.scene import SceneCanvas
from vispy.util.event import Event


class VispyCanvas(SceneCanvas):
    """Line-based vispy canvas"""

    view, grid, x_axis, y_axis = None, None, None, None

    def __init__(self, *args, **kwargs):
        # Since the base class is frozen we must create this attribute
        # before calling super().__init__().
        self.max_texture_sizes = None
        self._last_theme_color = None
        self._background_color_override = None
        super().__init__(*args, **kwargs)
        # Call get_max_texture_sizes() here so that we query OpenGL right now while we know a Canvas exists.
        # Later calls to get_max_texture_sizes() will return the same results because it's using an lru_cache.
        self.max_texture_sizes = get_max_texture_sizes()

        # enable hover events
        self._send_hover_events = True  # temporary workaround

        self.events.ignore_callback_errors = False
        self.native.setMinimumSize(QSize(200, 200))
        self.context.set_depth_func("lequal")

        # connect events
        self.events.mouse_double_click.connect(self._on_mouse_double_click)

        self.events.add(reset_view=Event, reset_x=Event, reset_y=Event, leave=Event, enter=Event)

    @property
    def destroyed(self):
        return self._backend.destroyed

    @property
    def background_color_override(self):
        """Get background color"""
        return self._background_color_override

    @background_color_override.setter
    def background_color_override(self, value):
        self._background_color_override = value
        self.bgcolor = value or self._last_theme_color

    def _on_theme_change(self, event):
        # store last requested theme color, in case we need to reuse it
        # when clearing the background_color_override, without needing to
        # keep track of the viewer.
        from napari.utils.theme import get_theme

        self._last_theme_color = get_theme(event.value)["canvas"]
        self.bgcolor = self._last_theme_color

    @property
    def bgcolor(self):
        """Get background color"""
        SceneCanvas.bgcolor.fget(self)

    @bgcolor.setter
    def bgcolor(self, value):
        _value = self._background_color_override or value
        SceneCanvas.bgcolor.fset(self, _value)

    @contextmanager
    def modify_context(self):
        """Modify context"""
        self.unfreeze()
        yield self
        self.freeze()

    def _on_mouse_double_click(self, event):
        """Process mouse double click event"""
        vis = self.visual_at(event.pos)
        # if user double-clicked in the canvas, reset the entire view
        if vis and event.button == 1:
            self.events.reset_view()
        else:
            x, y = event.pos
            x_x, x_y = self.x_axis.node.pos
            y_x, y_y = self.y_axis.node.pos
            # if clicked on the x-axis, reset x-range
            if x > y_x and y > x_y:
                self.events.reset_x()
            # if clicked on the y-axis, reset y-range
            elif x < x_x:
                self.events.reset_y()

    @property
    def camera(self):
        """Get camera associated with this view"""
        return self.view.camera
