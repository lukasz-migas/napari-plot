"""Draw batched rectangle strokes in framebuffer space."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from napari._vispy.visuals.markers import Markers
from vispy.gloo import IndexBuffer, VertexBuffer
from vispy.scene.visuals import Compound, Text
from vispy.visuals import Visual

if TYPE_CHECKING:
    from napari._vispy.utils.qt_font import FontInfo

_VERTEX_SHADER = """
attribute vec2 a_center;
attribute vec2 a_half_size;
attribute vec3 a_corner;
uniform float u_half_stroke;
varying vec4 v_color;

void main() {
    vec4 center = $to_framebuffer(vec4(a_center, 0.0, 1.0));
    // The plot is orthographic. Map the half axes as vectors so translation
    // and the magnitude of the center cannot wipe out small dimensions.
    vec4 x = $to_framebuffer(vec4(a_half_size.x, 0.0, 0.0, 0.0));
    vec4 y = $to_framebuffer(vec4(0.0, a_half_size.y, 0.0, 0.0));
    vec4 corner = center + a_corner.x * x + a_corner.y * y;
    vec2 u = x.xy * a_corner.x;
    vec2 v = y.xy * a_corner.y;
    float u_length = length(u);
    float v_length = length(v);
    u /= max(u_length, 1e-12);
    v /= max(v_length, 1e-12);

    // Adjacent edge normals point outward even if a plot axis is flipped.
    float cross_uv = u.x * v.y - u.y * v.x;
    float winding = cross_uv < 0.0 ? -1.0 : 1.0;
    vec2 normal_u = winding * vec2(v.y, -v.x);
    vec2 normal_v = winding * vec2(-u.y, u.x);
    vec2 miter = (normal_u + normal_v) / max(1.0 + dot(normal_u, normal_v), 1e-6);
    // Cap the outer miter for near-parallel axes. The inner ring may collapse
    // onto the center line but must never turn inside out and overlap.
    float outset = u_half_stroke * min(1.0, 4.0 / max(length(miter), 1.0));
    float inset = min(u_half_stroke, min(u_length, v_length) * abs(cross_uv));
    corner.xy += miter * (a_corner.z > 0.0 ? outset : -inset);
    gl_Position = $to_render(corner);
    v_color = $color;
}
"""

_FRAGMENT_SHADER = """
varying vec4 v_color;

void main() {
    gl_FragColor = v_color;
}
"""

_CORNERS = np.array(
    [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1), (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1)],
    dtype=np.float32,
)
_INDICES = np.array([0, 1, 5, 0, 5, 4, 1, 2, 6, 1, 6, 5, 2, 3, 7, 2, 7, 6, 3, 0, 4, 3, 4, 7], dtype=np.uint32)


class RectangleOutlineVisual(Visual):
    """Render one indexed batch of screen-space rectangle strokes."""

    def __init__(self) -> None:
        super().__init__(vcode=_VERTEX_SHADER, fcode=_FRAGMENT_SHADER)
        self._vertices = VertexBuffer()
        self._colors = VertexBuffer()
        self._index_buffer = IndexBuffer()
        self._draw_mode = "triangles"
        self._count = 0
        self._width = 1.0
        self.freeze()

    def set_geometry(self, data: np.ndarray) -> None:
        """Upload center and half-size attributes for the indexed stroke ring."""
        count = len(data)
        vertices = np.empty((count, 8), dtype=[("a_center", "2f"), ("a_half_size", "2f"), ("a_corner", "3f")])
        vertices["a_center"] = data[:, None, :2]
        vertices["a_half_size"] = data[:, None, 3:1:-1] * 0.5
        vertices["a_corner"] = _CORNERS
        self._vertices.set_data(vertices.ravel())
        self.shared_program.bind(self._vertices)
        if count != self._count:
            offsets = np.arange(count, dtype=np.uint32)[:, None] * 8
            self._index_buffer.set_data((offsets + _INDICES).ravel())
            self._count = count
        self.update()

    def set_color(self, color: np.ndarray) -> None:
        """Set a uniform stroke color or upload one color per rectangle."""
        if color.ndim == 1:
            self.shared_program.vert["color"] = tuple(color)
        else:
            self._colors.set_data(np.repeat(color, 8, axis=0))
            self.shared_program.vert["color"] = self._colors
        self.update()

    def set_width(self, width: float) -> None:
        """Set stroke width in logical screen pixels."""
        self._width = width
        self.update()

    def _prepare_transforms(self, view: Visual) -> None:
        view.view_program.vert["to_framebuffer"] = view.get_transform("visual", "framebuffer")
        view.view_program.vert["to_render"] = view.get_transform("framebuffer", "render")

    def _prepare_draw(self, view: Visual) -> bool:
        view.view_program["u_half_stroke"] = self._width * view.transforms.pixel_scale * 0.5
        return self._count > 0


class RectanglesVisual(Compound):
    """Draw outlines, center markers, and labels in that order."""

    def __init__(self, font_info: FontInfo) -> None:
        self.outlines = RectangleOutlineVisual()
        self.markers = Markers(scaling="fixed")
        self.text = Text(anchor_x="left", anchor_y="bottom", face=font_info.face, font_manager=font_info.font_manager)
        super().__init__([self.outlines, self.markers, self.text])
