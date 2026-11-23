"""Lay out napari's colorbar visual alongside a plot."""

from __future__ import annotations

import typing as ty

import numpy as np
from napari._vispy.visuals.colorbar import ColorBar as NapariColorBar
from napari.utils.colormaps.colormap_utils import _napari_cmap_to_vispy
from napari.utils.events import disconnect_events
from vispy.scene import Widget
from vispy.scene.widgets import Grid

from napari_plot._vispy.components.axis import _tick_label_sizes, default_tick_formatter
from napari_plot._vispy.plot_cell import detach_widget

if ty.TYPE_CHECKING:
    from napari._vispy.utils.qt_font import FontInfo

    from napari_plot.components.colorbar import ColorBar
    from napari_plot.components.viewer_model import ViewerModel

_GAP = 10
_TICK_LENGTH = 5
_TICK_LABEL_MARGIN = 8
_LABEL_GAP = 6
_PADDING = 8
_SAMPLES = 256


class VispyColorBarVisual:
    """Render a live color scale in a right or bottom gutter."""

    def __init__(self, viewer: ViewerModel, model: ColorBar, font_info: FontInfo) -> None:
        self._viewer = viewer
        self._model = model
        self._layout: tuple[Grid, int, int, int, Widget, float] | None = None
        self._slot: tuple[int, int, int] | None = None
        self.node = Widget()
        self._bar = NapariColorBar(font_info)
        self._bar.parent = self.node
        self.axis = self._bar.ticks
        self.axis.major_tick_length = _TICK_LENGTH
        self.axis.minor_tick_length = _TICK_LENGTH / 2
        self.axis.tick_label_margin = _TICK_LABEL_MARGIN
        self.node.events.resize.connect(self._on_resize)
        model.events.connect(self._update)
        viewer.events.theme.connect(self._update)
        for name in ("tick_color", "label_color", "tick_size", "label_size", "x_tick_formatter", "y_tick_formatter"):
            getattr(viewer.axis.events, name).connect(self._update)

    def place(
        self, grid: Grid, right_row: int, bottom_row: int, bottom_col: int, padding: Widget, bottom_span: int = 1
    ) -> None:
        """Attach to the named right and bottom slots of a plot layout."""
        if self._layout is not None:
            old_grid, old_row, old_bottom, old_col, old_padding, _default = self._layout
            if (grid, right_row, bottom_row, bottom_col, padding) == (
                old_grid,
                old_row,
                old_bottom,
                old_col,
                old_padding,
            ):
                return
            self.detach()
        self._layout = (grid, right_row, bottom_row, bottom_col, padding, float(padding.width_max))
        self._bottom_span = bottom_span
        self._update()

    def detach(self) -> None:
        """Release the gutter and remove the visual from its layout."""
        if self._layout is not None:
            grid, _, _, _, padding, default = self._layout
            padding.width_max = default
            grid._need_solver_recreate = True
            self._layout = None
        if isinstance(self.node.parent, Grid):
            detach_widget(self.node.parent, self.node)
        self._slot = None

    def _update(self, _event: ty.Any = None) -> None:
        self.node.visible = self._model.visible
        if self._layout is None:
            return
        grid, right_row, bottom_row, bottom_col, padding, default = self._layout
        vertical = self._model.position == "right"
        slot = (right_row, 2, 1) if vertical else (bottom_row, bottom_col, self._bottom_span)
        if self._slot != slot or not self.node.visible:
            if self.node.parent is grid:
                detach_widget(grid, self.node)
            self._slot = None
        if not self.node.visible:
            padding.width_max = default
            grid._need_solver_recreate = True
            grid.update()
            return
        if self._slot is None:
            grid.add_widget(self.node, row=slot[0], col=slot[1], col_span=slot[2])
            self._slot = slot

        model = self._model
        low, high = model.contrast_limits
        logarithmic = model.norm == "log" and 0 < low < high
        fractions = np.linspace(0, 1, _SAMPLES)
        if logarithmic:
            values = np.geomspace(low, high, _SAMPLES)
            fractions = (values - low) / (high - low)
        else:
            values = np.linspace(low, high, _SAMPLES)
        gradient = fractions[::-1, None] if vertical else fractions[None, :]
        self._bar.img.set_data(np.asarray(gradient, dtype=np.float32))
        self._bar.img.clim = (0, 1)
        self._bar.set_cmap(_napari_cmap_to_vispy(model.colormap))
        self._bar.set_gamma(model.gamma)

        style = self._viewer.axis
        tick_color, text_color = style.colors_for_theme(self._viewer.theme)
        self._bar.box.set_data(color=tick_color)
        self.axis.tick_color = tick_color
        self.axis.text_color = text_color
        self.axis.tick_font_size = style.tick_size
        self.axis.axis_font_size = style.label_size
        self.axis.tick_direction = (1, 0) if vertical else (0, 1)
        formatter = style.y_tick_formatter if vertical else style.x_tick_formatter
        self.axis.ticker.tick_format_func = formatter or default_tick_formatter
        self.axis.scale_type = "logarithmic" if logarithmic else "linear"
        self.axis.domain = tuple(np.log10((low, high))) if logarithmic else (low, high)
        self.axis.axis_label = model.label or None
        self.axis._axis_label_vis.visible = bool(model.label)

        labels = [self.axis.ticker.tick_format_func(float(value)) for value in values[:: _SAMPLES // 4]]
        try:
            widths, heights = _tick_label_sizes(self.axis, labels)
            tick_width, tick_height = float(widths.max()), float(heights.max())
        except AttributeError:
            tick_width, tick_height = 8 * max(map(len, labels)), style.tick_size * 1.5
        label_size = tick_height * style.label_size / max(style.tick_size, 1)
        tick_size = tick_width if vertical else tick_height
        label_offset = _TICK_LENGTH + _TICK_LABEL_MARGIN + tick_size + _LABEL_GAP
        self.axis._axis_label_margin = label_offset + label_size / 2
        thickness = _GAP + model.bar_width + label_offset + _PADDING + (label_size if model.label else 0)
        self.node.width_max = thickness if vertical else None
        self.node.height_max = None if vertical else thickness
        padding.width_max = thickness if vertical else default
        grid._need_solver_recreate = True
        self._on_resize()
        grid.update()

    def _on_resize(self, _event: ty.Any = None) -> None:
        if not self.node.visible or self._slot is None:
            return
        width, height = map(float, self.node.size)
        model = self._model
        size: tuple[float, float]
        if model.position == "right":
            length = max(1, height - 2 * _PADDING)
            size = model.bar_width, length
            origin = _GAP, _PADDING
            self.axis.pos = np.asarray(((_GAP + size[0], _PADDING + length), (_GAP + size[0], _PADDING)))
        else:
            length = max(1, width - 2 * _PADDING)
            size = length, model.bar_width
            origin = _PADDING, _GAP
            self.axis.pos = np.asarray(((_PADDING, _GAP + size[1]), (_PADDING + length, _GAP + size[1])))
        self._bar.box.transform.scale = size
        self._bar.box.transform.translate = origin
        gradient = self._bar.img
        gradient.transform.scale = (size[0] / gradient.size[0], size[1] / gradient.size[1])
        gradient.transform.translate = origin
        self.axis._need_update = True
        self.node.update()

    def close(self) -> None:
        """Disconnect from the plot and release the gutter."""
        self.detach()
        disconnect_events(self._model.events, self)
        disconnect_events(self._viewer.events, self)
        disconnect_events(self._viewer.axis.events, self)
