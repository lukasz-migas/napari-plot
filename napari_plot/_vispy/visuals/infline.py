"""Vispy visuals for infinite line layers."""

from __future__ import annotations

import typing as ty

import numpy as np
from vispy import gloo
from vispy.scene.visuals import Compound, InfiniteLine, Line, create_visual_node
from vispy.visuals import Visual

LINE_BOX = 0
HORIZONTAL_INFLINE = 1
VERTICAL_INFLINE = 2
BATCHED_INFLINES = 3

_VERTEX_SHADER = """
    attribute vec2 a_pos;
    attribute vec4 a_color;
    attribute float a_orientation;
    varying vec4 v_color;

    void main() {
        vec4 pos = vec4(a_pos, 0., 1.);

        if(a_orientation < 0.5)
        {
            pos.y = $render_to_visual(pos).y;
        }
        else
        {
            pos.x = $render_to_visual(pos).x;
        }

        gl_Position = $transform(pos);
        v_color = a_color;
    }
    """

_FRAGMENT_SHADER = """
    varying vec4 v_color;

    void main() {
        gl_FragColor = v_color;
    }
    """


class _BatchedInfiniteLineVisual(Visual):
    """Render multiple horizontal and vertical infinite lines in one draw call."""

    def __init__(self, line_width: float = 1.0, antialias: bool = False) -> None:
        super().__init__(vcode=_VERTEX_SHADER, fcode=_FRAGMENT_SHADER)

        self._pos_buf = gloo.VertexBuffer()
        self._color_buf = gloo.VertexBuffer()
        self._orientation_buf = gloo.VertexBuffer()
        self.shared_program["a_pos"] = self._pos_buf
        self.shared_program["a_color"] = self._color_buf
        self.shared_program["a_orientation"] = self._orientation_buf

        self._line_pos = np.zeros(0, dtype=np.float32)
        self._line_orientation = np.zeros(0, dtype=np.float32)
        self._line_color = np.zeros((0, 4), dtype=np.float32)
        self._vertex_pos = np.zeros((0, 2), dtype=np.float32)
        self._vertex_color = np.zeros((0, 4), dtype=np.float32)
        self._vertex_orientation = np.zeros(0, dtype=np.float32)
        self._line_width = float(line_width)
        self._antialias = bool(antialias)
        self._changed = True

        self._draw_mode = "lines"
        self.set_gl_state("translucent", depth_test=False)

    def set_data(
        self,
        pos: ty.Optional[np.ndarray] = None,
        orientation: ty.Optional[np.ndarray] = None,
        color: ty.Optional[np.ndarray] = None,
        width: ty.Optional[float] = None,
    ) -> None:
        """Set the positions, orientations, colors, or width of the batched lines."""
        if width is not None:
            self._line_width = float(width)

        if pos is not None:
            self._line_pos = np.asarray(pos, dtype=np.float32).reshape(-1)
        if orientation is not None:
            self._line_orientation = np.asarray(orientation, dtype=np.float32).reshape(-1)
        if color is not None:
            self._line_color = np.asarray(color, dtype=np.float32).reshape(-1, 4)

        if pos is not None or orientation is not None or color is not None:
            self._validate_line_data()
            self._rebuild_vertices()
            self._changed = True

        self.update()

    @property
    def pos(self) -> np.ndarray:
        """Return the scalar line positions."""
        return self._line_pos

    @property
    def orientation(self) -> np.ndarray:
        """Return the line orientation codes."""
        return self._line_orientation

    @property
    def color(self) -> np.ndarray:
        """Return one RGBA color per line."""
        return self._line_color

    @property
    def vertex_pos(self) -> np.ndarray:
        """Return the two GL vertices used for each line."""
        return self._vertex_pos

    @property
    def vertex_color(self) -> np.ndarray:
        """Return the expanded per-vertex RGBA colors."""
        return self._vertex_color

    @property
    def vertex_orientation(self) -> np.ndarray:
        """Return the expanded per-vertex orientation codes."""
        return self._vertex_orientation

    @property
    def line_width(self) -> float:
        """Return the line width in pixels."""
        return self._line_width

    @line_width.setter
    def line_width(self, value: float) -> None:
        self._line_width = float(value)
        self.update()

    @property
    def antialias(self) -> bool:
        """Return whether GL line smoothing is enabled."""
        return self._antialias

    @antialias.setter
    def antialias(self, value: bool) -> None:
        self._antialias = bool(value)
        self.update()

    def _validate_line_data(self) -> None:
        if len(self._line_pos) != len(self._line_orientation):
            raise ValueError("pos and orientation must have the same length.")
        if len(self._line_pos) != len(self._line_color):
            raise ValueError("pos and color must have the same length.")

    def _rebuild_vertices(self) -> None:
        n_lines = len(self._line_pos)
        self._vertex_pos = np.zeros((n_lines * 2, 2), dtype=np.float32)
        self._vertex_color = np.repeat(self._line_color, 2, axis=0).astype(np.float32, copy=False)
        self._vertex_orientation = np.repeat(self._line_orientation, 2).astype(np.float32, copy=False)

        if n_lines == 0:
            return

        vertical = self._line_orientation < 0.5
        horizontal = ~vertical

        self._vertex_pos[0::2, 0] = np.where(vertical, self._line_pos, -1.0)
        self._vertex_pos[1::2, 0] = np.where(vertical, self._line_pos, 1.0)
        self._vertex_pos[0::2, 1] = np.where(horizontal, self._line_pos, -1.0)
        self._vertex_pos[1::2, 1] = np.where(horizontal, self._line_pos, 1.0)

    def _compute_bounds(self, axis: int, view) -> ty.Optional[tuple[float, float]]:
        """Return finite bounds for the constrained line axis."""
        if len(self._line_pos) == 0:
            return None

        vertical = self._line_orientation < 0.5
        if axis == 0 and np.any(vertical):
            values = self._line_pos[vertical]
            return float(np.min(values)), float(np.max(values))

        horizontal = ~vertical
        if axis == 1 and np.any(horizontal):
            values = self._line_pos[horizontal]
            return float(np.min(values)), float(np.max(values))

        return None

    def _prepare_transforms(self, view=None) -> None:
        program = view.view_program
        transforms = view.transforms
        program.vert["render_to_visual"] = transforms.get_transform("render", "visual")
        program.vert["transform"] = transforms.get_transform("visual", "render")

    def _prepare_draw(self, view=None) -> bool:
        self.update_gl_state(line_smooth=self._antialias)
        width = self.transforms.pixel_scale * self._line_width
        self.update_gl_state(line_width=max(width, 1.0))

        if len(self._vertex_pos) == 0:
            return False

        if self._changed:
            self._pos_buf.set_data(self._vertex_pos)
            self._color_buf.set_data(self._vertex_color)
            self._orientation_buf.set_data(self._vertex_orientation)
            self._changed = False

        return True


_BatchedInfiniteLine = create_visual_node(_BatchedInfiniteLineVisual)


class InfLineVisual(Compound):
    """Compound vispy visual for infinite line visualisation.

    Components:
        - Line: Highlight box for selection.
        - InfiniteLine: Horizontal line used for drawing temporary lines.
        - InfiniteLine: Vertical line used for drawing temporary lines.
        - Batched infinite line: Stored infinite lines.
    """

    _opacity: float

    def __init__(self) -> None:
        super().__init__(
            [
                Line(),
                InfiniteLine(vertical=False),
                InfiniteLine(vertical=True),
                _BatchedInfiniteLine(),
            ]
        )
        self._opacity = 1.0

    @property
    def select_box(self) -> Line:
        """Selection box visual."""
        return self._subvisuals[LINE_BOX]

    @property
    def horizontal_visual(self) -> InfiniteLine:
        """Horizontal temporary infinite line visual."""
        return self._subvisuals[HORIZONTAL_INFLINE]

    @property
    def vertical_visual(self) -> InfiniteLine:
        """Vertical temporary infinite line visual."""
        return self._subvisuals[VERTICAL_INFLINE]

    @property
    def lines_visual(self) -> _BatchedInfiniteLine:
        """Batched visual for stored infinite lines."""
        return self._subvisuals[BATCHED_INFLINES]

    @property
    def opacity(self) -> float:
        """Opacity."""
        return self._opacity

    @opacity.setter
    def opacity(self, value: float) -> None:
        """Set opacity for stored and temporary line visuals."""
        self._opacity = float(value)
        self.horizontal_visual.opacity = self._opacity
        self.vertical_visual.opacity = self._opacity
        self.lines_visual.opacity = self._opacity
        self.select_box.opacity = 1.0
        self._update_opacity()
        self.update()

    @property
    def visible(self) -> bool:
        """Visible."""
        return self._vshare.visible

    @visible.setter
    def visible(self, value: bool) -> None:
        if value != self._vshare.visible:
            self._vshare.visible = value
            self.horizontal_visual.visible = value
            self.vertical_visual.visible = value
            self.lines_visual.visible = value
            self.update()
