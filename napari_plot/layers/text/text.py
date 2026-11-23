"""Text layer model."""

from __future__ import annotations

from collections.abc import Generator, Sequence
from enum import StrEnum
from typing import Any, ClassVar

import numpy as np
from napari.layers.base import no_op
from napari.layers.base._base_mouse_bindings import highlight_box_handles, transform_with_box
from napari.settings import get_settings
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import Event

from napari_plot.layers._thumbnail import TEXT
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


class TextMode(StrEnum):
    """Mouse modes for placing labels on the plot."""

    PAN_ZOOM = "pan_zoom"
    TRANSFORM = "transform"
    MOVE = "move"


def _move_text(layer: Text, event: Event) -> Generator[None, None, None]:
    if event.button != 1 or not layer.editable or getattr(event, "plot_selection_tool", False):
        return
    start = layer.world_to_data(event.position)
    index = layer._get_value(start)
    if index is None:
        return
    origin = layer.data[index].copy()
    event.handled = True
    yield
    while event.type in {"mouse_move", "mouse_release"}:
        if layer.mode != TextMode.MOVE or not layer.editable or index >= len(layer.data):
            return
        position = origin + (layer.world_to_data(event.position) - start)[::-1]
        if np.any(position != layer.data[index]):
            data = layer.data.copy()
            data[index] = position
            layer.data = data
        if event.type == "mouse_release":
            return
        yield


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


def _broadcast_offsets(value: Any, length: int, name: str = "offset") -> tuple[np.ndarray, np.ndarray | None]:
    """Broadcast one xy offset or validate one offset per label."""
    array = np.asarray(value, dtype=float)
    scalar = array.shape == (2,)
    if not np.all(np.isfinite(array)):
        raise ValueError(f"'{name}' values must be finite.")
    if scalar:
        fallback = array.copy()
        array = np.broadcast_to(array, (length, 2)).copy()
    elif array.shape == (length, 2):
        fallback = None
        array = array.copy()
    else:
        raise ValueError(f"'{name}' must be an (x, y) pair or an (N, 2) array.")
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

    Set ``mode`` to ``"move"`` to drag individual labels in the canvas.

    Parameters
    ----------
    data : array-like, shape (N, 2), optional
        Label positions in ``[x, y]`` order.
    text : str or sequence of str, optional
        Text to display. A string is broadcast to every coordinate.
    size : float, optional
        Layer-wide font size in screen points. None uses the application setting.
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
    pixel_offset : array-like, shape (2,) or (N, 2)
        Extra offset in screen pixels (x to the right, y up), added after ``offset``. Unlike ``offset`` it keeps
        labels at the same distance from their points at any zoom, like matplotlib's ``"offset points"``.
    font_face : str, optional
        Font family shared by the layer. By default the application font is used.
    bold : bool
        Whether to render the layer text in bold.
    italic : bool
        Whether to render the layer text in italics.
    """

    _modeclass = TextMode
    _drag_modes: ClassVar[dict] = {
        TextMode.PAN_ZOOM: no_op,
        TextMode.TRANSFORM: transform_with_box,
        TextMode.MOVE: _move_text,
    }
    _move_modes: ClassVar[dict] = {
        TextMode.PAN_ZOOM: no_op,
        TextMode.TRANSFORM: highlight_box_handles,
        TextMode.MOVE: no_op,
    }
    _cursor_modes: ClassVar[dict[TextMode, str]] = {
        TextMode.PAN_ZOOM: "standard",
        TextMode.TRANSFORM: "standard",
        TextMode.MOVE: "standard",
    }

    def __init__(
        self,
        data: Any = None,
        text: str | Sequence[str] | None = None,
        *,
        size: float | None = None,
        color: Any = "white",
        alignment: str = "center",
        vertical_alignment: str = "center",
        rotation: float | Sequence[float] = 0,
        offset: Any = (0, 0),
        pixel_offset: Any = (0, 0),
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
        size = None if size is None else _coerce_scalar(size, "size", positive=True)
        colors, default_color = _broadcast_colors(color, n_labels)
        alignment = _coerce_choice(alignment, "alignment", HORIZONTAL_ALIGNMENTS)
        vertical_alignment = _coerce_choice(
            vertical_alignment,
            "vertical_alignment",
            VERTICAL_ALIGNMENTS,
        )
        rotations, default_rotation = _broadcast_numeric(rotation, n_labels, "rotation")
        offsets, default_offset = _broadcast_offsets(offset, n_labels)
        pixel_offsets, default_pixel_offset = _broadcast_offsets(pixel_offset, n_labels, "pixel_offset")
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
        self._data_per_pixel: np.ndarray | None = None
        self.events.add(
            text=Event,
            size=Event,
            color=Event,
            alignment=Event,
            vertical_alignment=Event,
            rotation=Event,
            offset=Event,
            pixel_offset=Event,
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
        self._pixel_offset = pixel_offsets
        self._font_face = font_face
        self._bold = bool(bold)
        self._italic = bool(italic)

        self._default_color = transform_color("white")[0] if default_color is None else default_color
        self._default_rotation = 0.0 if default_rotation is None else default_rotation
        self._default_offset = np.zeros(2) if default_offset is None else default_offset
        self._default_pixel_offset = np.zeros(2) if default_pixel_offset is None else default_pixel_offset

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
                "pixel_offset": self.pixel_offset,
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
        self._pixel_offset = _resize_array(self._pixel_offset, length, self._default_pixel_offset)

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
    def size(self) -> float | None:
        """Return the layer-wide font size in screen points."""
        return self._size

    @property
    def effective_size(self) -> float:
        """Return the explicit font size or the application default."""
        return float(get_settings().appearance.font_size if self.size is None else self.size)

    @size.setter
    def size(self, value: float | None) -> None:
        self._size = None if value is None else _coerce_scalar(value, "size", positive=True)
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
        self._update_thumbnail()

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
    def pixel_offset(self) -> np.ndarray:
        """Return xy offsets in screen pixels (x to the right, y up)."""
        return self._pixel_offset

    @pixel_offset.setter
    def pixel_offset(self, value: Any) -> None:
        array, scalar = _broadcast_offsets(value, len(self.data), "pixel_offset")
        self._pixel_offset = array
        if scalar is not None:
            self._default_pixel_offset = scalar
        self.events.pixel_offset(value=array)

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
            em_size = extent_span * self.effective_size * _POINT_TO_PIXEL / _NOMINAL_VIEWPORT_SIZE
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

    def _update_draw(self, scale_factor: float, corner_pixels_displayed: Any, shape_threshold: Any) -> None:
        corners = np.asarray(corner_pixels_displayed, dtype=float)
        if corners.shape == (2, 2) and len(shape_threshold) == 2:
            width, height = shape_threshold
            # Transform screen x and y independently, including layer rotation and scale.
            origin = self.world_to_data(corners[0])
            x_step = self.world_to_data([corners[0, 0], corners[1, 1]]) - origin
            y_step = self.world_to_data([corners[1, 0], corners[0, 1]]) - origin
            self._data_per_pixel = np.stack((x_step[::-1] / max(width, 1), -y_step[::-1] / max(height, 1)))
        super()._update_draw(scale_factor, corners, shape_threshold)

    def _get_value(self, position: np.ndarray) -> int | None:
        """Return the topmost label at the given data-space position."""
        pixel = self._data_per_pixel
        if self.mode != TextMode.MOVE or not len(self.data) or pixel is None:
            return None
        em_size = self.effective_size * _POINT_TO_PIXEL
        anchors = self.data + self.offset + self.pixel_offset @ pixel
        xy = position[::-1]
        for index in range(len(self.data) - 1, -1, -1):
            if not self.text[index]:
                continue
            corners = _label_bounds(self.text[index], self.alignment, self.vertical_alignment, self.rotation[index])
            bounds = anchors[index] + em_size * (corners @ pixel)
            if np.all((xy >= bounds.min(axis=0)) & (xy <= bounds.max(axis=0))):
                return index
        return None

    def _on_editable_changed(self) -> None:
        if not self.editable:
            self.mode = TextMode.PAN_ZOOM

    def _update_thumbnail(self) -> None:
        color = self.color[0] if len(self.color) else self._default_color
        self._set_thumbnail_glyph(TEXT, color)
