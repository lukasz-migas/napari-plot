"""Coordinate transforms for nonlinear plot axes."""

from __future__ import annotations

import numpy as np
from vispy.visuals.transforms import BaseTransform, ChainTransform, LogTransform
from vispy.visuals.transforms._util import arg_to_array

from napari_plot.components.axis import AxisScale


class _PowerTransform(BaseTransform):
    """Apply a sign-preserving power to the x and y coordinates."""

    glsl_map = """
        vec4 plot_power_map(vec4 position) {
            position.xy = sign(position.xy) * pow(abs(position.xy), $power);
            return position;
        }
    """
    glsl_imap = glsl_map
    Linear = False
    Orthogonal = True
    NonScaling = False
    Isometric = False

    def __init__(self, powers: tuple[float, float]) -> None:
        super().__init__()
        self._powers = np.asarray(powers, dtype=np.float32)

    @arg_to_array
    def map(self, coords: np.ndarray) -> np.ndarray:
        """Apply the configured powers."""
        return self._apply(coords, self._powers)

    @arg_to_array
    def imap(self, coords: np.ndarray) -> np.ndarray:
        """Apply the inverse powers."""
        return self._apply(coords, 1 / self._powers)

    @staticmethod
    def _apply(coords: np.ndarray, powers: np.ndarray) -> np.ndarray:
        result = np.array(coords, dtype=float, copy=True)
        values = result[..., :2]
        values[:] = np.sign(values) * np.power(np.abs(values), powers)
        return result

    def shader_map(self):
        """Supply the powers to the vertex shader."""
        shader = super().shader_map()
        shader["power"] = self._powers
        return shader

    def shader_imap(self):
        """Supply the inverse powers to the vertex shader."""
        shader = super().shader_imap()
        shader["power"] = 1 / self._powers
        return shader


def axis_transform(x_scale: AxisScale, y_scale: AxisScale, x_power: float, y_power: float) -> BaseTransform:
    """Return the scene transformation for the two configured axes."""
    x_base = 10.0 if x_scale is AxisScale.LOG else 0.0
    y_base = 10.0 if y_scale is AxisScale.LOG else 0.0
    log = LogTransform((x_base, y_base, 0.0))
    if x_scale is AxisScale.POWER or y_scale is AxisScale.POWER:
        powers = (x_power if x_scale is AxisScale.POWER else 1.0, y_power if y_scale is AxisScale.POWER else 1.0)
        return ChainTransform([_PowerTransform(powers), log])
    return log
