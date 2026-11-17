"""Draw error intervals with thickness and caps measured in screen pixels."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from napari._vispy.layers.base import VispyBaseLayer
from vispy.gloo import IndexBuffer, VertexBuffer
from vispy.scene.visuals import create_visual_node
from vispy.visuals import Visual

if TYPE_CHECKING:
    from napari._vispy.utils.qt_font import FontInfo

    from napari_plot.layers.error_bar import ErrorBar

_VERTEX_SHADER = """
attribute vec2 a_start;
attribute vec2 a_end;
attribute vec2 a_corner;
attribute float a_cap;
uniform float u_half_width;
uniform float u_half_cap;

void main() {
    vec4 start = $to_framebuffer(vec4(a_start, 0.0, 1.0));
    vec4 end = $to_framebuffer(vec4(a_end, 0.0, 1.0));
    vec2 delta = end.xy - start.xy;
    vec2 along = delta / max(length(delta), 1e-6);
    vec2 normal = vec2(-along.y, along.x);

    vec4 vertex;
    if (a_cap < 0.0) {
        vertex = mix(start, end, a_corner.x);
        vertex.xy += a_corner.y * u_half_width * normal;
    } else {
        vertex = mix(start, end, a_cap);
        vertex.xy += a_corner.x * u_half_cap * normal + a_corner.y * u_half_width * along;
    }
    gl_Position = $to_render(vertex);
}
"""

_FRAGMENT_SHADER = """
uniform vec4 u_color;

void main() {
    gl_FragColor = u_color;
}
"""

# Four corners for the stem, then four for each cap. The last column identifies the piece.
_CORNERS = np.array(
    [
        (0, -1, -1),
        (1, -1, -1),
        (1, 1, -1),
        (0, 1, -1),
        (-1, -1, 0),
        (-1, 1, 0),
        (1, 1, 0),
        (1, -1, 0),
        (-1, -1, 1),
        (-1, 1, 1),
        (1, 1, 1),
        (1, -1, 1),
    ],
    dtype=np.float32,
)
_INDICES = np.array([0, 1, 2, 0, 2, 3, 4, 5, 6, 4, 6, 7, 8, 9, 10, 8, 10, 11], dtype=np.uint32)


class ErrorBarVisual(Visual):
    """Render all stems and caps in one indexed batch."""

    def __init__(self) -> None:
        super().__init__(vcode=_VERTEX_SHADER, fcode=_FRAGMENT_SHADER)
        self._vertices = VertexBuffer()
        self._index_buffer = IndexBuffer()
        self._draw_mode = "triangles"
        self._count = 0
        self._width = 1.0
        self._cap_size = 0.0
        self.freeze()

    def set_segments(self, segments: np.ndarray) -> None:
        """Upload (x, y) endpoints for each stem and its two caps."""
        count = len(segments)
        if count:
            vertices = np.empty(
                (count, len(_CORNERS)), dtype=[("a_start", "2f"), ("a_end", "2f"), ("a_corner", "2f"), ("a_cap", "f")]
            )
            vertices["a_start"] = segments[:, :1]
            vertices["a_end"] = segments[:, 1:]
            vertices["a_corner"] = _CORNERS[:, :2]
            vertices["a_cap"] = _CORNERS[:, 2]
            self._vertices.set_data(vertices.ravel())
            self.shared_program.bind(self._vertices)
            if count != self._count:
                offsets = np.arange(count, dtype=np.uint32)[:, None] * len(_CORNERS)
                self._index_buffer.set_data((offsets + _INDICES).ravel())
        self._count = count
        self.update()

    def set_style(self, color: np.ndarray, width: float, cap_size: float) -> None:
        """Set RGBA and logical pixel sizes without rebuilding geometry."""
        self.shared_program["u_color"] = tuple(color)
        self._width = width
        self._cap_size = cap_size
        self.update()

    def _prepare_transforms(self, view: Visual) -> None:
        view.view_program.vert["to_framebuffer"] = view.get_transform("visual", "framebuffer")
        view.view_program.vert["to_render"] = view.get_transform("framebuffer", "render")

    def _prepare_draw(self, view: Visual) -> bool:
        pixel_scale = view.transforms.pixel_scale
        view.view_program["u_half_width"] = self._width * pixel_scale / 2
        view.view_program["u_half_cap"] = self._cap_size * pixel_scale / 2
        return self._count > 0


_ErrorBarNode = create_visual_node(ErrorBarVisual)


class VispyErrorBarLayer(VispyBaseLayer):
    """Upload error intervals and keep their appearance in sync."""

    layer: ErrorBar
    node: ErrorBarVisual

    def __init__(self, layer: ErrorBar, font_info: FontInfo) -> None:
        super().__init__(layer, _ErrorBarNode(), font_info=font_info)
        layer.events.color.connect(self._on_style_change)
        layer.events.width.connect(self._on_style_change)
        layer.events.cap_size.connect(self._on_style_change)
        self.reset()
        self._on_style_change()
        self._on_data_change()

    def _on_data_change(self) -> None:
        self.node.set_segments(self.layer._segments())

    def _on_style_change(self) -> None:
        self.node.set_style(self.layer.color, self.layer.width, self.layer.cap_size)
