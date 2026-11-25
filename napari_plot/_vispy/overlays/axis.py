"""Axes visual"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar, Literal

import numpy as np
from vispy.scene import AxisWidget
from vispy.scene.widgets import Grid

from napari_plot._vispy.components.axis import _tick_label_sizes, rotated_label_growth
from napari_plot.components.axis import AxisScale

if TYPE_CHECKING:
    from napari.utils.events import Event

    from napari_plot.components.canvas import PlotGridCell


def _format_categories(categories: tuple[str, ...] | None, formatter: Callable[[str], str] | None) -> tuple[str, ...]:
    """Return the displayed categorical tick labels."""
    if not categories:
        return ()
    return categories if formatter is None else tuple(str(formatter(label)) for label in categories)


def _rotated_anchors(rotation: float) -> tuple[str, str] | None:
    """Return text anchors that put the end of a label rotated counter-clockwise by `rotation` at its tick."""
    if rotation == 0:
        return None
    vertical = "middle" if abs(rotation) >= 90 else "top"
    return ("right" if rotation > 0 else "left"), vertical


class VispyAxisVisual:
    """Axes visual"""

    node_kwargs: ClassVar[dict] = {}
    dimension: ClassVar[Literal["x", "y"]]

    def __init__(self, viewer, parent=None, order=1e6):
        self._viewer = viewer
        self._cell_model: PlotGridCell | None = None
        self._own_formatter = False

        self.node = AxisWidget(
            axis_font_size=10,
            axis_label_margin=50,
            axis_color="#FFFFFF",
            text_color="#FFFFFF",
            **self.node_kwargs,
        )
        self.node.order = order
        parent.add(self.node)

        self._suppressed = False
        self._viewer.axis.events.visible.connect(self._on_visible_change)
        self._viewer.axis.events.tick_color.connect(self._on_color_change)
        self._viewer.axis.events.label_color.connect(self._on_color_change)
        self._viewer.events.theme.connect(self._on_color_change)
        self._viewer.axis.events.tick_size.connect(self._on_size_change)
        self._viewer.axis.events.label_size.connect(self._on_size_change)
        for field in ("minor_ticks", "tick_notation", "power", "datetime_origin"):
            getattr(self._viewer.axis.events, f"{self.dimension}_{field}").connect(self._on_tick_options_change)

        self._on_visible_change(None)
        self._on_color_change(None)
        self._on_size_change(None)
        self._on_label_change(None)
        self._on_margin_change(None)
        self._on_max_size_change(None)
        self.on_tick_formatter_change(None)
        self._on_tick_options_change()

    def configure_cell(
        self, cell: PlotGridCell | None, *, label_visible: bool = True, own_formatter: bool = False
    ) -> None:
        """Apply the grid cell's axis settings, using the viewer's defaults for unspecified fields.

        With ``own_formatter``, the tick formatter comes only from the cell (``None`` is the default format).
        """
        self._cell_model = cell
        self._own_formatter = own_formatter and cell is not None
        self._on_scale_change()
        self._on_label_change()
        self.on_tick_formatter_change()
        self.node.axis._axis_label_vis.visible = label_visible

    def _axis_setting(self, field: str) -> Any:
        if field == "scale" and self._cell_model is not None:
            return self._cell_model.axis_scale(self.dimension, self._viewer.axis)
        name = f"{self.dimension}_{field}"
        value = getattr(self._cell_model, name, None)
        if field == "tick_formatter" and getattr(self, "_own_formatter", False):
            return value
        return getattr(self._viewer.axis, name) if value is None else value

    def _on_tick_options_change(self, _evt: Event | None = None) -> None:
        ticker = self.node.axis.ticker
        ticker.minor_ticks = self._axis_setting("minor_ticks")
        ticker.notation = self._axis_setting("tick_notation")
        ticker.power = self._axis_setting("power")
        ticker.datetime_origin = self._axis_setting("datetime_origin")
        self._refresh_tick_layout()

    def _on_visible_change(self, _evt=None):
        """Change grid lines visibility"""
        self.node.visible = self._viewer.axis.visible and not self._suppressed

    def suppress(self, suppressed: bool) -> None:
        """Hide this axis and collapse its gutter while preserving global settings."""
        self._suppressed = suppressed
        self._on_visible_change()
        self._on_max_size_change(None)

    def _on_color_change(self, _evt=None) -> None:
        """Update axis colors from explicit settings and the viewer theme."""
        tick_color, label_color = self._viewer.axis.colors_for_theme(self._viewer.theme)
        self.node.axis.axis_color = tick_color
        self.node.axis.tick_color = tick_color
        self.node.axis.text_color = label_color
        self.node.axis.update()

    def _on_size_change(self, _evt=None):
        """Change node size"""
        self.node.axis.tick_font_size = self._viewer.axis.tick_size
        self.node.axis.axis_font_size = self._viewer.axis.label_size
        self._update_label_space()
        self._refresh_tick_layout()

    def _update_label_space(self) -> None:
        """Make room for the tick labels (only needed by axes with long category labels)."""

    def _set_size_limit(self, name: str, value: float) -> None:
        """Set the `height_max` or `width_max` of the axis widget and make the grid apply it."""
        if self._suppressed:
            value = 0
        if value != getattr(self.node, name):
            setattr(self.node, name, value)
            # the grid turns size limits into layout constraints only when it rebuilds its solver
            grid = self.node.parent
            if isinstance(grid, Grid):
                grid._need_solver_recreate = True
                grid._update_child_widgets()

    def _refresh_tick_layout(self) -> None:
        """Recalculate tick positions and labels on the next draw."""
        self.node.axis._need_update = True
        self.node.axis.update()

    def on_tick_formatter_change(self, _evt=None):
        """Change tick formatter."""
        self.node.axis.ticker.tick_format_func = self._axis_setting("tick_formatter")
        self._refresh_tick_layout()

    def _on_label_change(self, _evt=None):
        """Change label"""
        label = self._axis_setting("label")
        self.node.axis.ticker.axis_label = label
        self.node.axis.axis_label = label

    def _on_scale_change(self, _evt=None) -> None:
        """Update the axis scale and categorical labels."""
        scale = self._axis_setting("scale")
        self.node.axis.scale_type = "logarithmic" if scale is AxisScale.LOG else scale.value
        self.node.axis.ticker.category_labels = _format_categories(
            self._axis_setting("categories"), self._axis_setting("category_formatter")
        )
        self._update_label_space()
        self._refresh_tick_layout()

    def _on_margin_change(self, _evt=None):
        """Change margin"""
        raise NotImplementedError("Must implement method")

    def _on_max_size_change(self, _evt=None):
        """Change the maximum width/height of the axis visual"""
        raise NotImplementedError("Must implement method")


class VispyXAxisVisual(VispyAxisVisual):
    """X-axis visual"""

    node_kwargs: ClassVar[dict] = {"orientation": "bottom", "tick_label_margin": 20}
    dimension = "x"

    def __init__(self, viewer, parent=None, order=1e6):
        super().__init__(viewer, parent, order)
        self._viewer.axis.events.x_label.connect(self._on_label_change)
        self._viewer.axis.events.x_label_margin.connect(self._on_margin_change)
        self._viewer.axis.events.x_tick_margin.connect(self._on_margin_change)
        self._viewer.axis.events.x_max_size.connect(self._on_max_size_change)
        self._viewer.axis.events.x_tick_formatter.connect(self.on_tick_formatter_change)
        self._viewer.axis.events.x_scale.connect(self._on_scale_change)
        self._viewer.axis.events.x_categories.connect(self._on_scale_change)
        self._viewer.axis.events.x_category_formatter.connect(self._on_scale_change)
        self._viewer.axis.events.x_tick_rotation.connect(self._on_rotation_change)
        self._viewer.axis.events.x_thin_categories.connect(self._on_thin_change)
        self._on_rotation_change()
        self._on_thin_change()
        self._on_scale_change()

    def _on_rotation_change(self, _evt=None) -> None:
        """Rotate the tick labels so that each one ends at its tick."""
        rotation = float(self._viewer.axis.x_tick_rotation)
        self.node.axis.ticker.label_rotation = rotation
        self.node.axis.ticker._anchors = _rotated_anchors(rotation)
        self.node.axis._text.rotation = -rotation  # vispy rotates clockwise
        self._update_label_space()
        self._refresh_tick_layout()

    def _on_thin_change(self, _evt=None) -> None:
        """Show or hide overlapping category labels."""
        self.node.axis.ticker.thin_categories = self._viewer.axis.x_thin_categories
        self._refresh_tick_layout()

    def _label_growth(self) -> float:
        """Return the extra height that rotated category labels need."""
        ticker = getattr(self.node.axis, "ticker", None)
        rotation = float(self._viewer.axis.x_tick_rotation)
        if ticker is None or rotation == 0 or self._axis_setting("scale") is not AxisScale.CATEGORICAL:
            return 0.0
        try:
            return rotated_label_growth(self.node.axis, ticker.category_labels, rotation)
        except AttributeError:  # not attached to a canvas yet
            return 0.0

    def _update_label_space(self) -> None:
        """Grow the axis and move its label down to fit rotated category labels."""
        growth = self._label_growth()
        self._set_size_limit("height_max", self._viewer.axis.x_max_size + growth)
        self.node.axis.axis_label_margin = self._viewer.axis.x_label_margin + growth
        self.node.axis._need_update = True
        self.node.update()

    def _on_margin_change(self, _evt=None):
        """Change margin"""
        self.node.axis.tick_label_margin = self._viewer.axis.x_tick_margin
        self._update_label_space()

    def _on_max_size_change(self, _evt=None):
        """Change the maximum width/height of the axis visual"""
        self._update_label_space()


class VispyYAxisVisual(VispyAxisVisual):
    """Y-axis visual"""

    node_kwargs: ClassVar[dict] = {"tick_label_margin": 10}
    dimension = "y"

    def __init__(self, viewer, parent=None, order=1e6):
        super().__init__(viewer, parent, order)
        self._viewer.axis.events.y_label.connect(self._on_label_change)
        self._viewer.axis.events.y_label_margin.connect(self._on_margin_change)
        self._viewer.axis.events.y_tick_margin.connect(self._on_margin_change)
        self._viewer.axis.events.y_max_size.connect(self._on_max_size_change)
        self._viewer.axis.events.y_tick_formatter.connect(self.on_tick_formatter_change)
        self._viewer.axis.events.y_scale.connect(self._on_scale_change)
        self._viewer.axis.events.y_categories.connect(self._on_scale_change)
        self._viewer.axis.events.y_category_formatter.connect(self._on_scale_change)
        self._viewer.axis.events.y_thin_categories.connect(self._on_thin_change)
        self._on_thin_change()
        self._on_scale_change()

    def _on_thin_change(self, _evt=None) -> None:
        """Show or hide overlapping category labels."""
        self.node.axis.ticker.thin_categories = self._viewer.axis.y_thin_categories
        self._refresh_tick_layout()

    def _on_margin_change(self, _evt=None):
        """Change margin"""
        self.node.axis.tick_label_margin = self._viewer.axis.y_tick_margin
        self._update_label_space()

    def _on_max_size_change(self, _evt=None):
        """Change the maximum width/height of the axis visual"""
        self._update_label_space()

    def _label_growth(self) -> float:
        """Return the extra width that category labels wider than the default label space need."""
        ticker = getattr(self.node.axis, "ticker", None)
        labels = getattr(ticker, "category_labels", ())
        if not labels or self._axis_setting("scale") is not AxisScale.CATEGORICAL:
            return 0.0
        try:
            widths, _ = _tick_label_sizes(self.node.axis, labels)
        except AttributeError:  # not attached to a canvas yet
            return 0.0
        # the axis title sits `y_label_margin` from the axis line: keep the tick labels and the title apart
        axis = self._viewer.axis
        needed = float(np.max(widths)) + axis.y_tick_margin + 2 * axis.label_size
        return max(0.0, needed - axis.y_label_margin)

    def _update_label_space(self) -> None:
        """Widen the axis and move its title out to fit long category labels."""
        growth = self._label_growth()
        self._set_size_limit("width_max", self._viewer.axis.y_max_size + growth)
        self.node.axis.axis_label_margin = self._viewer.axis.y_label_margin + growth
        self.node.axis._need_update = True
        self.node.update()
