"""Axes visual"""
from vispy.scene import AxisWidget

from .utils import tick_formatter


class VispyAxisVisual:
    """Axes visual"""

    node_kwargs = {}

    def __init__(self, viewer, parent=None, order=1e6):
        self._viewer = viewer

        self.node = AxisWidget(
            axis_font_size=10,
            axis_label_margin=50,
            axis_color="#FFFFFF",
            text_color="#FFFFFF",
            **self.node_kwargs,
        )
        self.node.order = order
        parent.add(self.node)

        self._viewer.camera.events.zoom.connect(self.node._view_changed)
        self._viewer.axis.events.visible.connect(self._on_visible_change)
        self._viewer.axis.events.tick_color.connect(self._on_color_change)
        self._viewer.axis.events.label_color.connect(self._on_color_change)
        self._viewer.axis.events.tick_size.connect(self._on_size_change)
        self._viewer.axis.events.label_size.connect(self._on_size_change)

        self._on_visible_change(None)
        self._on_color_change(None)
        self._on_size_change(None)
        self._on_label_change(None)
        self._on_margin_change(None)
        self._on_max_size_change(None)

    def _on_visible_change(self, _evt=None):
        """Change grid lines visibility"""
        self.node.visible = self._viewer.axis.visible

    def _on_color_change(self, _evt=None):
        """Change node color"""
        self.node.axis.axis_color = self._viewer.axis.tick_color
        self.node.axis.tick_color = self._viewer.axis.tick_color
        self.node.axis.label_color = self._viewer.axis.label_color
        self.node.axis.update()

    def _on_size_change(self, _evt=None):
        """Change node size"""
        self.node.axis.tick_font_size = self._viewer.axis.tick_size
        self.node.axis.axis_font_size = self._viewer.axis.label_size
        self.node.axis.update()

    def _on_label_change(self, _evt=None):
        """Change label"""
        raise NotImplementedError("Must implement method")

    def _on_margin_change(self, _evt=None):
        """Change margin"""
        raise NotImplementedError("Must implement method")

    def _on_max_size_change(self, _evt=None):
        """Change the maximum width/height of the axis visual"""
        raise NotImplementedError("Must implement method")


class VispyXAxisVisual(VispyAxisVisual):
    """X-axis visual"""

    node_kwargs = {"orientation": "bottom", "tick_label_margin": 20}

    def __init__(self, viewer, parent=None, order=1e6):
        super().__init__(viewer, parent, order)
        self._viewer.axis.events.x_label.connect(self._on_label_change)
        self._viewer.axis.events.x_label_margin.connect(self._on_margin_change)
        self._viewer.axis.events.x_tick_margin.connect(self._on_margin_change)
        self._viewer.axis.events.x_max_size.connect(self._on_max_size_change)

    def _on_label_change(self, _evt=None):
        """Change label"""
        self.node.axis.axis_label = self._viewer.axis.x_label

    def _on_margin_change(self, _evt=None):
        """Change margin"""
        self.node.axis.axis_label_margin = self._viewer.axis.x_label_margin
        self.node.axis.tick_label_margin = self._viewer.axis.x_tick_margin
        self.node.axis._need_update = True
        self.node.update()

    def _on_max_size_change(self, _evt=None):
        """Change the maximum width/height of the axis visual"""
        self.node.height_max = self._viewer.axis.x_max_size


class VispyYAxisVisual(VispyAxisVisual):
    """Y-axis visual"""

    node_kwargs = {"tick_label_margin": 10}

    def __init__(self, viewer, parent=None, order=1e6):
        super().__init__(viewer, parent, order)
        self.node.axis.ticker.tick_format_func = tick_formatter
        self._viewer.axis.events.y_label.connect(self._on_label_change)
        self._viewer.axis.events.y_label_margin.connect(self._on_margin_change)
        self._viewer.axis.events.y_tick_margin.connect(self._on_margin_change)
        self._viewer.axis.events.y_max_size.connect(self._on_max_size_change)

    def _on_label_change(self, _evt=None):
        """Change label"""
        self.node.axis.axis_label = self._viewer.axis.y_label

    def _on_margin_change(self, _evt=None):
        """Change margin"""
        self.node.axis.axis_label_margin = self._viewer.axis.y_label_margin
        self.node.axis.tick_label_margin = self._viewer.axis.y_tick_margin
        self.node.axis._need_update = True
        self.node.update()

    def _on_max_size_change(self, _evt=None):
        """Change the maximum width/height of the axis visual"""
        self.node.width_max = self._viewer.axis.y_max_size
