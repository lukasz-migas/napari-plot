"""Compound VisPy visual for finite bars."""

from vispy.scene.visuals import Compound, Line, Mesh


class BarVisual(Compound):
    """Mesh fills plus line-segment borders for a Bar layer."""

    def __init__(self) -> None:
        super().__init__([Mesh(), Line(connect="segments")])

    @property
    def mesh(self) -> Mesh:
        """Filled bar mesh visual."""
        return self._subvisuals[0]

    @property
    def border(self) -> Line:
        """Bar border line visual."""
        return self._subvisuals[1]


__all__ = ["BarVisual"]
