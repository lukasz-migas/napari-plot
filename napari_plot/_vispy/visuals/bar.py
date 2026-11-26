"""Compound VisPy visual for finite bars."""

import numpy as np
from vispy.scene.visuals import Compound, Line, Mesh
from vispy.visuals.shaders import Function


class _ColoredMesh(Mesh):
    """Mesh with per-vertex or per-face colors that keeps its shader program when its data changes.

    vispy's mesh builds a new (identical) color function on every data update, which counts as a shader code change,
    so the program was compiled again for each update; reusing one function makes an update a buffer upload only.
    """

    def __init__(self) -> None:
        super().__init__()
        self.unfreeze()
        self._pass_color: Function | None = None
        self.freeze()

    def _build_color_transform(self, colors: np.ndarray) -> Function:
        if colors.ndim == 2 and colors.shape[1] == 1:
            return super()._build_color_transform(colors)  # colormapped values
        if self._pass_color is None:
            self._pass_color = super()._build_color_transform(colors)
        return self._pass_color


class BarVisual(Compound):
    """Mesh fills plus line-segment borders for a Bar layer."""

    def __init__(self) -> None:
        super().__init__([_ColoredMesh(), Line(connect="segments")])

    @property
    def mesh(self) -> Mesh:
        """Filled bar mesh visual."""
        return self._subvisuals[0]

    @property
    def border(self) -> Line:
        """Bar border line visual."""
        return self._subvisuals[1]


__all__ = ["BarVisual"]
