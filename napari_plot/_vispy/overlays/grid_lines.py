"""Plot grid lines visual."""

from __future__ import annotations

import typing as ty

import numpy as np
from napari._vispy.overlays.base import ViewerOverlayMixin, VispyCanvasOverlay
from napari.utils.color import ColorValue, _contrast_ratio
from vispy.scene import Line, ViewBox

if ty.TYPE_CHECKING:
    from napari._vispy.utils.qt_font import FontInfo
    from napari.utils.events import Event
    from vispy.util.event import Event as VispyEvent
    from vispy.visuals import LineVisual

    from napari_plot._vispy.canvas import NapariSceneCanvas
    from napari_plot.components.grid_lines import GridLinesOverlay
    from napari_plot.components.viewer_model import ViewerModel

_BLACK = ColorValue("black")
_WHITE = ColorValue("white")


def auto_grid_color(background: ty.Any) -> ColorValue:
    """Return black or white, whichever has the higher contrast against ``background``."""
    return max((_BLACK, _WHITE), key=lambda candidate: _contrast_ratio(candidate, background))


class _GridLines(Line):
    """Draw grid lines in the plot view's local coordinates."""

    def __init__(self) -> None:
        self._last_layout: tuple[tuple[float, float], ...] | None = None
        self._last_origins: list[tuple[np.ndarray, ...]] = [(), ()]
        self._has_lines = False
        self.minor = False
        super().__init__(connect="segments", width=0.5)

    def _prepare_draw(self, view: LineVisual) -> bool | None:
        canvas: NapariSceneCanvas | None = self.canvas
        plot = self.parent
        if canvas is None or not isinstance(plot, ViewBox):
            return False

        bounds = plot.inner_rect
        if min(bounds.size) <= 0:
            return False
        limits = ((bounds.left, bounds.right), (bounds.bottom, bounds.top))
        # each plot cell (grid mode) has its own axes
        x_axis, y_axis = canvas.view_axes.get(plot, (canvas.x_axis, canvas.y_axis))
        widgets = (x_axis.node, y_axis.node)
        origins: list[tuple[np.ndarray, ...]] = []
        for widget in widgets:
            axis = widget.axis
            if axis.pos is None:
                origins.append(())
                continue
            # The grid can draw before its axes and needs their current layout.
            if axis._need_update:
                if np.array_equal(axis.pos[0], axis.pos[1]):
                    origins.append(())
                    continue
                axis._update_subvisuals()
            major = axis.ticker.major_tick_origins
            origins.append((major, axis.ticker.minor_tick_origins) if self.minor else (major,))

        layout = (*limits, plot.pos, widgets[0].pos, widgets[1].pos)
        same_origins = all(
            len(current) == len(previous) and all(a is b for a, b in zip(current, previous, strict=True))
            for current, previous in zip(origins, self._last_origins, strict=True)
        )
        if layout == self._last_layout and same_origins:
            return super()._prepare_draw(view) if self._has_lines else False
        self._last_layout = layout
        self._last_origins = origins

        segments = []
        for dimension, (widget, tick_origins) in enumerate(zip(widgets, origins, strict=True)):
            if not tick_origins:
                continue
            ticks = widget.node_transform(plot).map(np.concatenate(tick_origins))[:, dimension]
            low, high = limits[dimension]
            ticks = ticks[(ticks >= low) & (ticks <= high)]
            if not len(ticks):
                continue

            points = np.empty((2 * len(ticks), 2))
            points[:, dimension] = np.repeat(ticks, 2)
            points[:, 1 - dimension] = np.tile(limits[1 - dimension], len(ticks))
            segments.append(points)

        self._has_lines = bool(segments)
        if not self._has_lines:
            return False
        positions = np.concatenate(segments)
        if not np.array_equal(positions, self.pos):
            self.set_data(pos=positions)
        return super()._prepare_draw(view)


class VispyGridLinesOverlay(ViewerOverlayMixin, VispyCanvasOverlay):
    """Grid lines visual."""

    overlay: GridLinesOverlay
    node: _GridLines

    def __init__(
        self,
        *,
        viewer: ViewerModel,
        overlay: GridLinesOverlay,
        font_info: FontInfo,
        parent: ViewBox | None = None,
    ) -> None:
        super().__init__(node=_GridLines(), viewer=viewer, overlay=overlay, font_info=font_info, parent=parent)

        self.overlay.events.color.connect(self._on_color_change)
        self.overlay.events.minor.connect(self._on_minor_change)
        self.overlay.events.width.connect(self._on_width_change)
        self._scene_canvas: NapariSceneCanvas | None = self.node.canvas
        if self._scene_canvas is None:
            self.viewer.canvas.events.background_color.connect(self._on_color_change)
        else:
            self._scene_canvas.events.background_color.connect(self._on_color_change)
        self.reset()
        self._on_color_change()
        self._on_minor_change()
        self._on_width_change()

    def _on_minor_change(self, _event: Event | None = None) -> None:
        self.node.minor = self.overlay.minor
        self.node.update()

    def _on_width_change(self, _event: Event | None = None) -> None:
        if self.node.width != self.overlay.width:
            self.node.set_data(width=self.overlay.width)

    def _on_color_change(self, _event: VispyEvent | None = None) -> None:
        color = self.overlay.color
        if color is None:
            background = (
                self._scene_canvas.bgcolor.rgba
                if self._scene_canvas is not None
                else self.viewer.canvas.background_color
            )
            color = auto_grid_color(background)
        if not np.array_equal(color, self.node.color):
            self.node.set_data(color=color)

    def on_set_visible(self, _event: Event | None = None) -> None:
        """Toggle the grid lines."""
        self.overlay.visible = not self.overlay.visible

    def close(self) -> None:
        """Disconnect the color override and close the visual."""
        self.overlay.events.color.disconnect(self._on_color_change)
        self.overlay.events.minor.disconnect(self._on_minor_change)
        self.overlay.events.width.disconnect(self._on_width_change)
        if self._scene_canvas is not None:
            self._scene_canvas.events.background_color.disconnect(self._on_color_change)
        super().close()
