"""Vispy visuals for infinite region layers."""

from __future__ import annotations

import typing as ty

import numpy as np
from vispy import gloo
from vispy.scene.visuals import Compound, Line, LinearRegion, create_visual_node
from vispy.visuals import Visual

LINE_BOX = 0
HORIZONTAL_REGION = 1
VERTICAL_REGION = 2
BATCHED_REGIONS = 3

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


class _BatchedLinearRegionVisual(Visual):
    """Render multiple horizontal and vertical infinite regions in one draw call."""

    def __init__(self) -> None:
        super().__init__(vcode=_VERTEX_SHADER, fcode=_FRAGMENT_SHADER)

        self._pos_buf = gloo.VertexBuffer()
        self._color_buf = gloo.VertexBuffer()
        self._orientation_buf = gloo.VertexBuffer()
        self._index_buf = gloo.IndexBuffer()
        self.shared_program["a_pos"] = self._pos_buf
        self.shared_program["a_color"] = self._color_buf
        self.shared_program["a_orientation"] = self._orientation_buf
        self._vshare.index_buffer = self._index_buf

        self._region_pos = np.zeros((0, 2), dtype=np.float32)
        self._region_orientation = np.zeros(0, dtype=np.float32)
        self._region_color = np.zeros((0, 4), dtype=np.float32)
        self._vertex_pos = np.zeros((0, 2), dtype=np.float32)
        self._vertex_color = np.zeros((0, 4), dtype=np.float32)
        self._vertex_orientation = np.zeros(0, dtype=np.float32)
        self._indices = np.zeros(0, dtype=np.uint32)
        self._changed = True

        self._draw_mode = "triangles"
        self.set_gl_state("translucent", depth_test=False)

    def set_data(
        self,
        pos: ty.Optional[np.ndarray] = None,
        orientation: ty.Optional[np.ndarray] = None,
        color: ty.Optional[np.ndarray] = None,
    ) -> None:
        """Set the bounds, orientations, or colors of the batched regions."""
        if pos is not None:
            self._region_pos = np.asarray(pos, dtype=np.float32).reshape(-1, 2)
        if orientation is not None:
            self._region_orientation = np.asarray(orientation, dtype=np.float32).reshape(-1)
        if color is not None:
            self._region_color = np.asarray(color, dtype=np.float32).reshape(-1, 4)

        if pos is not None or orientation is not None or color is not None:
            self._validate_region_data()
            self._rebuild_vertices()
            self._changed = True

        self.update()

    @property
    def pos(self) -> np.ndarray:
        """Return one pair of bounds per region."""
        return self._region_pos

    @property
    def orientation(self) -> np.ndarray:
        """Return the region orientation codes."""
        return self._region_orientation

    @property
    def color(self) -> np.ndarray:
        """Return one RGBA color per region."""
        return self._region_color

    @property
    def vertex_pos(self) -> np.ndarray:
        """Return the four GL vertices used for each region."""
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
    def indices(self) -> np.ndarray:
        """Return the triangle indices used to draw each region separately."""
        return self._indices

    def _validate_region_data(self) -> None:
        if len(self._region_pos) != len(self._region_orientation):
            raise ValueError("pos and orientation must have the same length.")
        if len(self._region_pos) != len(self._region_color):
            raise ValueError("pos and color must have the same length.")

    def _rebuild_vertices(self) -> None:
        n_regions = len(self._region_pos)
        self._vertex_pos = np.zeros((n_regions * 4, 2), dtype=np.float32)
        self._vertex_color = np.repeat(self._region_color, 4, axis=0).astype(np.float32, copy=False)
        self._vertex_orientation = np.repeat(self._region_orientation, 4).astype(np.float32, copy=False)
        self._indices = np.zeros(n_regions * 6, dtype=np.uint32)

        if n_regions == 0:
            return

        vertical = self._region_orientation < 0.5
        horizontal = ~vertical
        start = self._region_pos[:, 0]
        stop = self._region_pos[:, 1]

        self._vertex_pos[0::4, 0] = np.where(vertical, start, 1.0)
        self._vertex_pos[1::4, 0] = np.where(vertical, start, -1.0)
        self._vertex_pos[2::4, 0] = np.where(vertical, stop, 1.0)
        self._vertex_pos[3::4, 0] = np.where(vertical, stop, -1.0)
        self._vertex_pos[0::4, 1] = np.where(horizontal, start, -1.0)
        self._vertex_pos[1::4, 1] = np.where(horizontal, start, 1.0)
        self._vertex_pos[2::4, 1] = np.where(horizontal, stop, -1.0)
        self._vertex_pos[3::4, 1] = np.where(horizontal, stop, 1.0)

        base = np.arange(n_regions, dtype=np.uint32) * 4
        self._indices.reshape(-1, 6)[:] = np.column_stack(
            [
                base,
                base + 1,
                base + 2,
                base + 1,
                base + 2,
                base + 3,
            ]
        )

    def _compute_bounds(self, axis: int, view) -> ty.Optional[tuple[float, float]]:
        """Return finite bounds for the constrained region axis."""
        if len(self._region_pos) == 0:
            return None

        vertical = self._region_orientation < 0.5
        if axis == 0 and np.any(vertical):
            values = self._region_pos[vertical]
            return float(np.min(values)), float(np.max(values))

        horizontal = ~vertical
        if axis == 1 and np.any(horizontal):
            values = self._region_pos[horizontal]
            return float(np.min(values)), float(np.max(values))

        return None

    def _prepare_transforms(self, view=None) -> None:
        program = view.view_program
        transforms = view.transforms
        program.vert["render_to_visual"] = transforms.get_transform("render", "visual")
        program.vert["transform"] = transforms.get_transform("visual", "render")

    def _prepare_draw(self, view=None) -> bool:
        if len(self._vertex_pos) == 0:
            return False

        if self._changed:
            self._pos_buf.set_data(self._vertex_pos)
            self._color_buf.set_data(self._vertex_color)
            self._orientation_buf.set_data(self._vertex_orientation)
            self._index_buf.set_data(self._indices)
            self._changed = False

        return True


_BatchedLinearRegion = create_visual_node(_BatchedLinearRegionVisual)


class RegionVisual(Compound):
    """Compound vispy visual for infinite region visualisation.

    Components:
        - Line: Highlight box for selection.
        - LinearRegion: Horizontal region used for drawing temporary regions.
        - LinearRegion: Vertical region used for drawing temporary regions.
        - Batched linear region: Stored infinite regions.
    """

    _opacity: float

    def __init__(self) -> None:
        super().__init__(
            [
                Line(),
                LinearRegion([0, 0], [0, 0, 0, 0], vertical=False),
                LinearRegion([0, 0], [0, 0, 0, 0], vertical=True),
                _BatchedLinearRegion(),
            ]
        )
        self._opacity = 1.0

    @property
    def select_box(self) -> Line:
        """Selection box visual."""
        return self._subvisuals[LINE_BOX]

    @property
    def horizontal_visual(self) -> LinearRegion:
        """Horizontal temporary region visual."""
        return self._subvisuals[HORIZONTAL_REGION]

    @property
    def vertical_visual(self) -> LinearRegion:
        """Vertical temporary region visual."""
        return self._subvisuals[VERTICAL_REGION]

    @property
    def regions_visual(self) -> _BatchedLinearRegion:
        """Batched visual for stored infinite regions."""
        return self._subvisuals[BATCHED_REGIONS]

    @property
    def opacity(self) -> float:
        """Opacity."""
        return self._opacity

    @opacity.setter
    def opacity(self, value: float) -> None:
        """Set opacity for stored and temporary region visuals."""
        self._opacity = float(value)
        self.horizontal_visual.opacity = self._opacity
        self.vertical_visual.opacity = self._opacity
        self.regions_visual.opacity = self._opacity
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
            self.regions_visual.visible = value
            self.update()
