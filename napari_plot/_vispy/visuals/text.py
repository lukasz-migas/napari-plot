"""Text visual whose labels can be shifted by a fixed number of screen pixels."""

from __future__ import annotations

import typing as ty

import numpy as np
from vispy.scene.visuals import create_visual_node
from vispy.visuals.text import text as _vispy_text


def _with_pixel_offset(vertex_shader: str) -> str:
    """Add an `a_px_offset` attribute (logical pixels, y up) to the glyph offset of vispy's text vertex shader."""
    anchor = "attribute vec3 a_pos;  // anchor position"
    final = "gl_Position = vec4(pos.xyz + offset.xyz * pos.w, pos.w);"
    if anchor not in vertex_shader or final not in vertex_shader:
        raise RuntimeError("Unsupported vispy text shader; cannot add pixel offsets.")
    vertex_shader = vertex_shader.replace(anchor, f"{anchor}\n    attribute vec2 a_px_offset;  // in logical pixels")
    # u_px_scale converts one logical pixel to normalized device coordinates (with y pointing up)
    return vertex_shader.replace(final, f"offset.xy += a_px_offset * u_px_scale;\n        {final}")


class PixelOffsetTextVisual(_vispy_text.TextVisual):
    """vispy `TextVisual` with an extra shift in screen pixels for each label, which does not change with zoom."""

    _shaders: ty.ClassVar[dict[str, str]] = {
        "vertex": _with_pixel_offset(_vispy_text._VERTEX_SHADER),
        "fragment": _vispy_text._FRAGMENT_SHADER,
    }

    def __init__(self, *args, **kwargs) -> None:
        self._pixel_offset = np.zeros((1, 2), dtype=np.float32)
        self._pixel_offset_changed = True
        super().__init__(*args, **kwargs)

    @property
    def pixel_offset(self) -> np.ndarray:
        """Shift of each label in logical pixels (x to the right, y up); one row is shared by every label."""
        return self._pixel_offset

    @pixel_offset.setter
    def pixel_offset(self, value: np.ndarray) -> None:
        self._pixel_offset = np.atleast_2d(np.asarray(value, dtype=np.float32))
        self._pixel_offset_changed = True
        self.update()

    def _prepare_draw(self, view) -> bool | None:
        # the parent rebuilds the glyph buffer when the positions change, so the per-glyph offsets must follow
        update_offsets = self._pixel_offset_changed or self._pos_changed or self._vertices is None
        result = super()._prepare_draw(view)
        if result is False:
            return result
        if update_offsets:
            text = [self.text] if isinstance(self.text, str) else self.text
            repeats = [4 * len(label) for label in text]
            offsets = self._pixel_offset
            if len(offsets) < len(repeats):  # labels without an offset of their own reuse the last one
                offsets = np.vstack([offsets, np.repeat(offsets[-1:], len(repeats) - len(offsets), axis=0)])
            self.shared_program["a_px_offset"] = np.repeat(offsets[: len(repeats)], repeats, axis=0)
            self._pixel_offset_changed = False
        return result


PixelOffsetText = create_visual_node(PixelOffsetTextVisual)
