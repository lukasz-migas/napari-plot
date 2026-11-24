"""Crosshair visual."""

from __future__ import annotations

import typing as ty

import numpy as np
from napari._vispy.overlays.base import ViewerOverlayMixin, VispyCanvasOverlay
from vispy.scene import Line, Text, ViewBox

from napari_plot.utils.hover import format_coordinates

if ty.TYPE_CHECKING:
    from napari._vispy.utils.qt_font import FontInfo
    from napari.utils.events import Event
    from vispy.visuals import LineVisual

    from napari_plot._vispy.canvas import NapariSceneCanvas
    from napari_plot.components.crosshair import CrosshairOverlay
    from napari_plot.components.viewer_model import ViewerModel

# distance, in pixels, between the crosshair center and its coordinate label
_LABEL_OFFSET = 6.0


class _Crosshair(Line):
    """Draw the crosshair in the plot view's local coordinates, mapping the data point through the cell's axes."""

    def __init__(self) -> None:
        self.point: tuple[float, float] | None = None
        self.show_coordinates = True
        super().__init__(connect="segments", width=1.0)
        self.unfreeze()
        self.label = Text("", anchor_x="left", anchor_y="bottom", font_size=8, parent=self)
        self.freeze()

    def _prepare_draw(self, view: LineVisual) -> bool | None:
        canvas: NapariSceneCanvas | None = self.canvas
        plot = self.parent
        if canvas is None or not isinstance(plot, ViewBox) or self.point is None:
            self.label.visible = False
            return False
        scene = canvas.view_data_scenes.get(plot)
        bounds = plot.inner_rect
        if scene is None or min(bounds.size) <= 0:
            self.label.visible = False
            return False
        with np.errstate(invalid="ignore", divide="ignore"):
            x, y = scene.node_transform(plot).map(np.array([self.point], dtype=float))[0, :2]
        if not (np.isfinite(x) and np.isfinite(y)):
            self.label.visible = False
            return False
        positions = np.array(
            [[x, bounds.bottom], [x, bounds.top], [bounds.left, y], [bounds.right, y]],
            dtype=np.float32,
        )
        if not np.array_equal(positions, self.pos):
            self.set_data(pos=positions)
        self.label.visible = self.show_coordinates
        if self.show_coordinates:
            text = format_coordinates(*self.point)
            if self.label.text != text:
                self.label.text = text
            self.label.color = self.color
            self.label.pos = (x + _LABEL_OFFSET, y - _LABEL_OFFSET)
        return super()._prepare_draw(view)


class VispyCrosshairOverlay(ViewerOverlayMixin, VispyCanvasOverlay):
    """Crosshair visual; it is not tiled, so its size stays zero."""

    overlay: CrosshairOverlay
    node: _Crosshair

    def __init__(
        self,
        *,
        viewer: ViewerModel,
        overlay: CrosshairOverlay,
        font_info: FontInfo,
        parent: ViewBox | None = None,
    ) -> None:
        super().__init__(node=_Crosshair(), viewer=viewer, overlay=overlay, font_info=font_info, parent=parent)
        self.node.order = 1_000_000  # draw on top of every layer
        self.overlay.events.point.connect(self._on_point_change)
        self.overlay.events.color.connect(self._on_style_change)
        self.overlay.events.width.connect(self._on_style_change)
        self.overlay.events.show_coordinates.connect(self._on_point_change)
        self.viewer.axis.events.tick_color.connect(self._on_style_change)
        self.viewer.events.theme.connect(self._on_style_change)
        self.reset()
        self._on_style_change()
        self._on_point_change()

    def _on_point_change(self, _event: Event | None = None) -> None:
        self.node.point = self.overlay.point
        self.node.show_coordinates = self.overlay.show_coordinates
        self.node.update()

    def _on_style_change(self, _event: Event | None = None) -> None:
        color = self.overlay.color
        if color is None:
            color = self.viewer.axis.colors_for_theme(self.viewer.theme)[0]
        self.node.set_data(color=np.asarray(color, dtype=np.float32), width=self.overlay.width)
        self.node.label.color = color

    def _on_font_size_change(self) -> None:
        self.node.label.font_size = self._default_font_size

    def _on_position_change(self, _event: Event | None = None) -> None:
        """The crosshair follows the data, so it is never tiled."""

    def close(self) -> None:
        """Disconnect the model events and close the visual."""
        self.overlay.events.point.disconnect(self._on_point_change)
        self.overlay.events.color.disconnect(self._on_style_change)
        self.overlay.events.width.disconnect(self._on_style_change)
        self.overlay.events.show_coordinates.disconnect(self._on_point_change)
        self.viewer.axis.events.tick_color.disconnect(self._on_style_change)
        self.viewer.events.theme.disconnect(self._on_style_change)
        super().close()
