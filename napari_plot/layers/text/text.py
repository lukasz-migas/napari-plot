"""Text layer model."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import Event

from napari_plot.layers.base import BaseLayer

HORIZONTAL_ALIGNMENTS = frozenset({"left", "center", "right"})
VERTICAL_ALIGNMENTS = frozenset({"top", "center", "baseline", "bottom"})

# VisPy renders text in screen points. Estimate its data-space footprint using
# the viewer's default 400 px viewport at 96 DPI and common font proportions.
_AVERAGE_GLYPH_WIDTH = 0.6
_LINE_HEIGHT = 1.1
# Leave room for font-specific metrics and clipping at the viewport boundary.
_TEXT_BOUNDS_PADDING = 1.25
_NOMINAL_VIEWPORT_SIZE = 400.0
_POINT_TO_PIXEL = 4.0 / 3.0
_BASELINE_DESCENT = 0.2
_MAX_EXTENT_REFINEMENTS = 8


def _coerce_data(data: Any) -> np.ndarray:
    """Return xy coordinates as an ``(N, 2)`` floating-point array."""
    if data is None:
        return np.empty((0, 2), dtype=float)
    array = np.asarray(data, dtype=float)
    if array.size == 0:
        return np.empty((0, 2), dtype=float)
    if array.ndim != 2 or array.shape[1] != 2:
        raise ValueError("Text data must be an (N, 2) array of [x, y] coordinates.")
    return array


def _broadcast_numeric(
    value: Any,
    length: int,
    name: str,
    *,
    positive: bool = False,
) -> tuple[np.ndarray, float | None]:
    """Broadcast a scalar or validate a one-dimensional numeric array."""
    array = np.asarray(value, dtype=float)
    scalar = array.ndim == 0
    if scalar and (not np.isfinite(array) or (positive and array <= 0)):
        qualifier = "greater than zero" if positive else "finite"
        raise ValueError(f"'{name}' values must be {qualifier}.")
    if scalar:
        array = np.full(length, float(array), dtype=float)
    elif array.ndim != 1 or len(array) != length:
        raise ValueError(f"'{name}' must be a scalar or an array with one value per label.")
    else:
        array = array.astype(float, copy=True)
    if not np.all(np.isfinite(array)):
        raise ValueError(f"'{name}' values must be finite.")
    if positive and np.any(array <= 0):
        raise ValueError(f"'{name}' values must be greater than zero.")
    return array, float(np.asarray(value)) if scalar else None


def _coerce_scalar(value: Any, name: str, *, positive: bool = False) -> float:
    """Return one finite numeric style value."""
    array = np.asarray(value, dtype=float)
    if array.ndim != 0:
        raise ValueError(f"'{name}' must be a scalar value.")
    result = float(array)
    if not np.isfinite(result):
        raise ValueError(f"'{name}' must be finite.")
    if positive and result <= 0:
        raise ValueError(f"'{name}' must be greater than zero.")
    return result


def _coerce_choice(value: Any, name: str, valid: frozenset[str]) -> str:
    """Return one validated string style value."""
    if not isinstance(value, str):
        raise TypeError(f"'{name}' must be a string.")
    if value not in valid:
        choices = ", ".join(sorted(valid))
        raise ValueError(f"Invalid '{name}' value {value!r}; expected one of: {choices}.")
    return value


def _broadcast_text(value: str | Sequence[str] | None, length: int) -> np.ndarray:
    """Broadcast text or validate one label per coordinate."""
    if value is None:
        return np.full(length, "", dtype=object)
    if isinstance(value, str):
        return np.full(length, value, dtype=object)
    array = np.asarray(value, dtype=object)
    if array.ndim != 1 or len(array) != length:
        raise ValueError("'text' must be a string or an array with one value per coordinate.")
    if not all(isinstance(item, str) for item in array):
        raise TypeError("'text' values must be strings.")
    return array.copy()


def _broadcast_offsets(value: Any, length: int) -> tuple[np.ndarray, np.ndarray | None]:
    """Broadcast one xy offset or validate one offset per label."""
    array = np.asarray(value, dtype=float)
    scalar = array.shape == (2,)
    if not np.all(np.isfinite(array)):
        raise ValueError("'offset' values must be finite.")
    if scalar:
        fallback = array.copy()
        array = np.broadcast_to(array, (length, 2)).copy()
    elif array.shape == (length, 2):
        fallback = None
        array = array.copy()
    else:
        raise ValueError("'offset' must be an (x, y) pair or an (N, 2) array.")
    return array, fallback


def _broadcast_colors(value: Any, length: int) -> tuple[np.ndarray, np.ndarray | None]:
    """Broadcast one color or validate one color per label."""
    colors = transform_color(value)
    if len(colors) == 1:
        return np.broadcast_to(colors, (length, 4)).copy(), colors[0].copy()
    if len(colors) != length:
        raise ValueError("'color' must be one color or an array with one color per label.")
    return colors.copy(), None


def _resize_array(array: np.ndarray, length: int, fallback: Any) -> np.ndarray:
    """Resize a per-label array, repeating its final or fallback value."""
    current = len(array)
    if length <= current:
        return array[:length].copy()
    fill = array[-1] if current else fallback
    extra = np.broadcast_to(fill, (length - current, *array.shape[1:])).copy()
    return np.concatenate((array, extra), axis=0)


def _anchor_bounds(length: float, alignment: str, *, baseline: bool = False) -> tuple[float, float]:
    """Return bounds relative to an anchor for one text dimension."""
    if alignment in {"left", "top"}:
        return 0.0, length
    if alignment in {"right", "bottom"}:
        return -length, 0.0
    if baseline:
        return -_BASELINE_DESCENT * length, (1.0 - _BASELINE_DESCENT) * length
    return -length / 2.0, length / 2.0


def _label_bounds(
    text: str,
    alignment: str,
    vertical_alignment: str,
    rotation: float,
) -> np.ndarray:
    """Estimate one label's rotated bounds in font-em units."""
    if not text:
        return np.zeros((4, 2), dtype=float)

    lines = text.splitlines() or [""]
    width = max(map(len, lines)) * _AVERAGE_GLYPH_WIDTH * _TEXT_BOUNDS_PADDING
    height = len(lines) * _LINE_HEIGHT * _TEXT_BOUNDS_PADDING
    x_min, x_max = _anchor_bounds(width, alignment)
    y_min, y_max = _anchor_bounds(
        height,
        vertical_alignment,
        baseline=vertical_alignment == "baseline",
    )
    corners = np.array(
        [[x_min, y_min], [x_min, y_max], [x_max, y_min], [x_max, y_max]],
        dtype=float,
    )

    angle = np.deg2rad(rotation)
    cosine = np.cos(angle)
    sine = np.sin(angle)
    clockwise_rotation = np.array([[cosine, -sine], [sine, cosine]])
    return corners @ clockwise_rotation


class Text(BaseLayer):
    """Display text labels at xy plot coordinates.

    Parameters
    ----------
    data : array-like, shape (N, 2), optional
        Label positions in ``[x, y]`` order.
    text : str or sequence of str, optional
        Text to display. A string is broadcast to every coordinate.
    size : float
        Layer-wide font size in screen points.
    color : color-like or sequence of color-like
        Text color, either shared or one color per label.
    alignment : str
        Layer-wide horizontal anchor: ``left``, ``center``, or ``right``.
    vertical_alignment : str
        Layer-wide vertical anchor: ``top``, ``center``, ``baseline``, or ``bottom``.
    rotation : float or array-like of float
        Clockwise rotation in degrees, either shared or one value per label.
    offset : array-like, shape (2,) or (N, 2)
        Offset from each xy coordinate in plot data units.
    font_face : str, optional
        Font family shared by the layer. By default the application font is used.
    bold : bool
        Whether to render the layer text in bold.
    italic : bool
        Whether to render the layer text in italics.
    """

    def __init__(
        self,
        data: Any = None,
        text: str | Sequence[str] | None = None,
        *,
        size: float = 12,
        color: Any = "white",
        alignment: str = "center",
        vertical_alignment: str = "center",
        rotation: float | Sequence[float] = 0,
        offset: Any = (0, 0),
        font_face: str | None = None,
        bold: bool = False,
        italic: bool = False,
        axis_labels: Sequence[str] | None = None,
        name: str | None = None,
        metadata: dict | None = None,
        scale: Sequence[float] | None = None,
        translate: Sequence[float] | None = None,
        rotate: float | Sequence[float] | None = None,
        shear: float | Sequence[float] | None = None,
        affine: Any = None,
        opacity: float = 1.0,
        blending: str = "translucent",
        experimental_clipping_planes: Any = None,
        projection_mode: str = "none",
        units: Any = None,
        visible: bool = True,
    ) -> None:
        coordinates = _coerce_data(data)
        n_labels = len(coordinates)
        labels = _broadcast_text(text, n_labels)
        size = _coerce_scalar(size, "size", positive=True)
        colors, default_color = _broadcast_colors(color, n_labels)
        alignment = _coerce_choice(alignment, "alignment", HORIZONTAL_ALIGNMENTS)
        vertical_alignment = _coerce_choice(
            vertical_alignment,
            "vertical_alignment",
            VERTICAL_ALIGNMENTS,
        )
        rotations, default_rotation = _broadcast_numeric(rotation, n_labels, "rotation")
        offsets, default_offset = _broadcast_offsets(offset, n_labels)
        if font_face is not None and not isinstance(font_face, str):
            raise TypeError("'font_face' must be a string or None.")

        super().__init__(
            coordinates,
            axis_labels=axis_labels,
            name=name,
            metadata=metadata,
            scale=scale,
            translate=translate,
            rotate=rotate,
            shear=shear,
            affine=affine,
            opacity=opacity,
            blending=blending,
            experimental_clipping_planes=experimental_clipping_planes,
            projection_mode=projection_mode,
            units=units,
            visible=visible,
        )
        self.events.add(
            text=Event,
            size=Event,
            color=Event,
            alignment=Event,
            vertical_alignment=Event,
            rotation=Event,
            offset=Event,
            font_face=Event,
            bold=Event,
            italic=Event,
        )

        self._data = coordinates
        self._text = labels
        self._size = size
        self._color = colors
        self._alignment = alignment
        self._vertical_alignment = vertical_alignment
        self._rotation = rotations
        self._offset = offsets
        self._font_face = font_face
        self._bold = bool(bold)
        self._italic = bool(italic)

        self._default_color = transform_color("white")[0] if default_color is None else default_color
        self._default_rotation = 0.0 if default_rotation is None else default_rotation
        self._default_offset = np.zeros(2) if default_offset is None else default_offset

    def _get_state(self) -> dict[str, Any]:
        """Return the layer state used for duplication and serialization."""
        state = self._get_base_state()
        state.update(
            {
                "data": self.data,
                "text": self.text,
                "size": self.size,
                "color": self.color,
                "alignment": self.alignment,
                "vertical_alignment": self.vertical_alignment,
                "rotation": self.rotation,
                "offset": self.offset,
                "font_face": self.font_face,
                "bold": self.bold,
                "italic": self.italic,
            }
        )
        return state

    @property
    def data(self) -> np.ndarray:
        """Return label positions in ``[x, y]`` order."""
        return self._data

    @data.setter
    def data(self, value: Any) -> None:
        coordinates = _coerce_data(value)
        self._resize_attributes(len(coordinates))
        self._data = coordinates
        self._emit_new_data()

    def _resize_attributes(self, length: int) -> None:
        """Resize all arrays associated with label positions."""
        if not hasattr(self, "_text"):
            return
        current = len(self._text)
        self._text = self._text[:length].copy()
        if length > current:
            self._text = np.concatenate((self._text, np.full(length - current, "", dtype=object)))
        self._color = _resize_array(self._color, length, self._default_color)
        self._rotation = _resize_array(self._rotation, length, self._default_rotation)
        self._offset = _resize_array(self._offset, length, self._default_offset)

    @property
    def text(self) -> np.ndarray:
        """Return one text label per coordinate."""
        return self._text

    @text.setter
    def text(self, value: str | Sequence[str] | None) -> None:
        self._text = _broadcast_text(value, len(self.data))
        self._clear_extent()
        self.events.text(value=self._text)

    @property
    def size(self) -> float:
        """Return the layer-wide font size in screen points."""
        return self._size

    @size.setter
    def size(self, value: float) -> None:
        self._size = _coerce_scalar(value, "size", positive=True)
        self._clear_extent()
        self.events.size(value=self._size)

    @property
    def color(self) -> np.ndarray:
        """Return text colors as an ``(N, 4)`` RGBA array."""
        return self._color

    @color.setter
    def color(self, value: Any) -> None:
        array, scalar = _broadcast_colors(value, len(self.data))
        self._color = array
        if scalar is not None:
            self._default_color = scalar
        self.events.color(value=array)

    @property
    def alignment(self) -> str:
        """Return the layer-wide horizontal alignment."""
        return self._alignment

    @alignment.setter
    def alignment(self, value: str) -> None:
        self._alignment = _coerce_choice(value, "alignment", HORIZONTAL_ALIGNMENTS)
        self._clear_extent()
        self.events.alignment(value=self._alignment)

    @property
    def vertical_alignment(self) -> str:
        """Return the layer-wide vertical alignment."""
        return self._vertical_alignment

    @vertical_alignment.setter
    def vertical_alignment(self, value: str) -> None:
        self._vertical_alignment = _coerce_choice(
            value,
            "vertical_alignment",
            VERTICAL_ALIGNMENTS,
        )
        self._clear_extent()
        self.events.vertical_alignment(value=self._vertical_alignment)

    @property
    def rotation(self) -> np.ndarray:
        """Return clockwise rotations in degrees."""
        return self._rotation

    @rotation.setter
    def rotation(self, value: float | Sequence[float]) -> None:
        array, scalar = _broadcast_numeric(value, len(self.data), "rotation")
        self._rotation = array
        if scalar is not None:
            self._default_rotation = scalar
        self._clear_extent()
        self.events.rotation(value=array)

    @property
    def offset(self) -> np.ndarray:
        """Return xy offsets in plot data units."""
        return self._offset

    @offset.setter
    def offset(self, value: Any) -> None:
        array, scalar = _broadcast_offsets(value, len(self.data))
        self._offset = array
        if scalar is not None:
            self._default_offset = scalar
        self._clear_extent()
        self.events.offset(value=array)

    @property
    def font_face(self) -> str | None:
        """Return the layer-wide font family."""
        return self._font_face

    @font_face.setter
    def font_face(self, value: str | None) -> None:
        if value is not None and not isinstance(value, str):
            raise TypeError("'font_face' must be a string or None.")
        self._font_face = value
        self.events.font_face(value=value)

    @property
    def bold(self) -> bool:
        """Return whether text is bold."""
        return self._bold

    @bold.setter
    def bold(self, value: bool) -> None:
        self._bold = bool(value)
        self.events.bold(value=self._bold)

    @property
    def italic(self) -> bool:
        """Return whether text is italic."""
        return self._italic

    @italic.setter
    def italic(self, value: bool) -> None:
        self._italic = bool(value)
        self.events.italic(value=self._italic)

    @property
    def x(self) -> np.ndarray:
        """Return x coordinates."""
        return self.data[:, 0]

    @x.setter
    def x(self, value: Sequence[float]) -> None:
        array = np.asarray(value, dtype=float)
        if array.ndim != 1 or len(array) != len(self.data):
            raise ValueError("The x array must contain one value per label.")
        self._data[:, 0] = array
        self._emit_new_data()

    @property
    def y(self) -> np.ndarray:
        """Return y coordinates."""
        return self.data[:, 1]

    @y.setter
    def y(self, value: Sequence[float]) -> None:
        array = np.asarray(value, dtype=float)
        if array.ndim != 1 or len(array) != len(self.data):
            raise ValueError("The y array must contain one value per label.")
        self._data[:, 1] = array
        self._emit_new_data()

    @property
    def _view_data(self) -> np.ndarray:
        """Return currently displayed xy coordinates."""
        return self.data

    @property
    def _extent_data(self) -> np.ndarray:
        """Return estimated label bounds in data coordinates."""
        if len(self.data) == 0:
            return np.full((2, 2), np.nan)

        positions = self.data + self.offset
        span = np.ptp(positions, axis=0)
        nonzero_span = span[span > 0]
        fallback_span = float(np.max(nonzero_span)) if len(nonzero_span) else 1.0
        span[span == 0] = fallback_span

        extent_span = span.copy()
        for _ in range(_MAX_EXTENT_REFINEMENTS):
            em_size = extent_span * self.size * _POINT_TO_PIXEL / _NOMINAL_VIEWPORT_SIZE
            bounds = []
            for position, text, rotation in zip(
                positions,
                self.text,
                self.rotation,
                strict=True,
            ):
                local_bounds = _label_bounds(
                    text,
                    self.alignment,
                    self.vertical_alignment,
                    rotation,
                )
                bounds.append(position + local_bounds * em_size)

            bounds_array = np.concatenate(bounds, axis=0)
            refined_span = np.maximum(np.ptp(bounds_array, axis=0), span)
            if np.allclose(refined_span, extent_span):
                break
            extent_span = refined_span

        minimum = np.min(bounds_array, axis=0)[::-1]
        maximum = np.max(bounds_array, axis=0)[::-1]
        return np.vstack((minimum, maximum))

    def _set_view_slice(self) -> None:
        self.events.set_data()

    def _get_value(self, position: np.ndarray) -> None:
        """Return no value because labels do not implement hit testing."""
        return

    def _update_thumbnail(self) -> None:
        """Render a simple text-like thumbnail glyph."""
        thumbnail = np.zeros(self._thumbnail_shape)
        height, width = self._thumbnail_shape[:2]
        color = self.color[0] if len(self.color) else self._default_color
        for row, span in ((height // 3, width // 2), (height // 2, width // 3)):
            start = (width - span) // 2
            thumbnail[row : row + 2, start : start + span] = color
        thumbnail[..., 3] *= self.opacity
        self.thumbnail = thumbnail
