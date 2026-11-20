"""Colorbar drawn in its own column to the right of the plot."""

from __future__ import annotations

import typing as ty

import numpy as np
from vispy.scene import Widget
from vispy.scene.visuals import Axis, Image, Line
from vispy.scene.widgets import Grid
from vispy.visuals.transforms import STTransform

from napari_plot._vispy.components.axis import _tick_label_sizes

if ty.TYPE_CHECKING:
    from napari_plot.components.viewer_model import ViewerModel

_GAP = 10  # px between the plot and the bar
_TICK_LENGTH = 5
_TICK_LABEL_MARGIN = 8
_LABEL_MARGIN = 6
_RIGHT_PADDING = 6
_N_COLORS = 256


class VispyColorBarVisual:
    """Colorbar (gradient, ticks and label) next to the plot, sized to its tick labels.

    The bar lives in the grid column right of the plot, which otherwise only holds a small padding widget; while the
    bar is visible that column is widened to fit it.
    """

    def __init__(self, viewer: ViewerModel, grid: Grid, padding: Widget, default_width: float) -> None:
        self._viewer = viewer
        self._grid = grid
        self._padding = padding
        self._default_width = default_width

        self.node = Widget()
        grid.add_widget(self.node, row=1, col=2)
        self._gradient = Image(parent=self.node, interpolation="nearest")
        self._gradient.transform = STTransform()
        self._border = Line(parent=self.node, color="white", width=1, connect="strip", method="gl")
        self.axis = Axis(
            parent=self.node,
            tick_direction=(1.0, 0.0),
            major_tick_length=_TICK_LENGTH,
            minor_tick_length=_TICK_LENGTH / 2,
            tick_label_margin=_TICK_LABEL_MARGIN,
            tick_width=1,
            axis_width=1,
        )

        colorbar = self._viewer.colorbar
        colorbar.events.visible.connect(self._on_visible_change)
        colorbar.events.colormap.connect(self._on_colormap_change)
        colorbar.events.contrast_limits.connect(self._on_layout_change)
        colorbar.events.label.connect(self._on_layout_change)
        colorbar.events.bar_width.connect(self._on_layout_change)
        for event in ("tick_color", "label_color", "tick_size", "label_size", "y_tick_formatter"):
            getattr(self._viewer.axis.events, event).connect(self._on_style_change)
        self.node.events.resize.connect(self._on_resize)

        self._on_colormap_change()
        self._on_style_change()
        self._on_visible_change()

    def _on_visible_change(self, _event: ty.Any = None) -> None:
        """Show or hide the bar and give the plot back its space when hidden."""
        self.node.visible = self._viewer.colorbar.visible
        self._on_layout_change()

    def _on_colormap_change(self, _event: ty.Any = None) -> None:
        """Draw the gradient with the highest value at the top."""
        colors = self._viewer.colorbar.colormap.map(np.linspace(1.0, 0.0, _N_COLORS))
        self._gradient.set_data(np.asarray(colors, dtype=np.float32)[:, None, :])
        self.node.update()

    def _on_style_change(self, _event: ty.Any = None) -> None:
        """Use the same colors, fonts and tick formatter as the plot axes."""
        axis = self._viewer.axis
        self.axis.axis_color = axis.tick_color
        self.axis.tick_color = axis.tick_color
        self.axis.text_color = axis.label_color
        self.axis.tick_font_size = axis.tick_size
        self.axis.axis_font_size = axis.label_size
        if axis.y_tick_formatter is not None:
            self.axis.ticker.tick_format_func = axis.y_tick_formatter
        self._border.set_data(color=axis.tick_color)
        self._on_layout_change()

    def _text_sizes(self) -> tuple[float, float]:
        """Return the widest tick label and the height of the label text in logical pixels."""
        low, high = self._viewer.colorbar.contrast_limits
        samples = [self.axis.ticker.tick_format_func(float(value)) for value in np.linspace(low, high, 5)]
        try:
            widths, heights = _tick_label_sizes(self.axis, samples)
            tick_width, tick_height = float(widths.max()), float(heights.max())
        except AttributeError:  # not attached to a canvas yet
            tick_width, tick_height = 8.0 * max(len(sample) for sample in samples), 12.0
        label_height = tick_height * self._viewer.axis.label_size / max(self._viewer.axis.tick_size, 1)
        return tick_width, label_height

    def _label_offset(self, tick_width: float) -> float:
        """Return the distance from the bar to the start of the label."""
        return _TICK_LENGTH + _TICK_LABEL_MARGIN + tick_width + _LABEL_MARGIN

    def required_width(self) -> float:
        """Return the width of the column needed for the bar, its tick labels and its label."""
        colorbar = self._viewer.colorbar
        tick_width, label_height = self._text_sizes()
        width = _GAP + colorbar.bar_width + self._label_offset(tick_width) + _RIGHT_PADDING
        return width + label_height if colorbar.label else width

    def _on_layout_change(self, _event: ty.Any = None) -> None:
        """Resize the grid column and redraw the bar."""
        width = self.required_width() if self._viewer.colorbar.visible else self._default_width
        if width != self._padding.width_max:
            # the column width is set by the padding widget above the bar; the grid only applies size limits when it
            # rebuilds its solver
            self._padding.width_max = width
            self.node.width_max = width
            self._grid._need_solver_recreate = True
            self._grid._update_child_widgets()
        self._on_resize()

    def _on_resize(self, _event: ty.Any = None) -> None:
        """Place the gradient, border, axis and label inside the widget."""
        colorbar = self._viewer.colorbar
        if not colorbar.visible:
            return
        height = float(self.node.size[1])
        if height <= 0:
            return
        x0, x1 = float(_GAP), float(_GAP + colorbar.bar_width)
        top, bottom = 0.0, height
        self._gradient.transform.scale = (colorbar.bar_width, height / _N_COLORS)
        self._gradient.transform.translate = (x0, top)
        self._border.set_data(pos=np.array([[x0, top], [x1, top], [x1, bottom], [x0, bottom], [x0, top]]))
        low, high = colorbar.contrast_limits
        self.axis.pos = np.array([[x1, bottom], [x1, top]])
        self.axis.domain = (low, high) if high > low else (low, low + 1.0)
        self.axis.axis_label = colorbar.label or None
        tick_width, label_height = self._text_sizes()
        # the axis places the center of its label this far from the axis line
        self.axis.axis_label_margin = self._label_offset(tick_width) + label_height / 2
        self.axis._need_update = True
        self.node.update()
