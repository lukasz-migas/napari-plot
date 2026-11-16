"""Axis-aligned rectangle outlines, center markers, and labels."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
from napari.layers.base import ActionType
from napari.layers.points._points_constants import SYMBOL_DICT
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import Event

from napari_plot.layers.base import BaseLayer

if TYPE_CHECKING:
    from collections.abc import Sequence

    from napari.utils.transforms import Affine
    from numpy.typing import ArrayLike

_DEFAULT_COLOR = (1.0, 1.0, 1.0, 1.0)
_DEFAULT_MARKER_SIZE = 6.0
_DEFAULT_MARKER_SYMBOL = "disc"


def _positive(value: float, name: str) -> float:
    if np.ndim(value) != 0:
        raise ValueError(f"{name} must be a scalar.")
    number = float(value)
    if not np.isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be finite and positive.")
    return number


def _sizes(value: ArrayLike, count: int, name: str) -> float | np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.ndim == 0:
        return _positive(float(array), name)
    if array.shape != (count,) or not np.all(np.isfinite(array) & (array > 0)):
        raise ValueError(f"{name} must be a positive scalar or contain one finite, positive value per rectangle.")
    return array.copy()


def _geometry(data: ArrayLike | None, height: ArrayLike | None, width: ArrayLike | None) -> np.ndarray:
    array = np.asarray([] if data is None else data, dtype=float)
    if height is None and width is None:
        if array.shape == (0,):
            array = array.reshape(0, 4)
        if array.ndim != 2 or array.shape[1] != 4:
            raise ValueError("Rectangles data must have [x, y, height, width] rows.")
        if not np.all(np.isfinite(array)) or np.any(array[:, 2:] <= 0):
            raise ValueError("Rectangle coordinates must be finite and dimensions must be finite and positive.")
        array = array.copy()
    else:
        if height is None or width is None:
            raise ValueError("Provide both height and width with rectangle centers.")
        if array.shape == (0,):
            array = array.reshape(0, 2)
        if array.ndim != 2 or array.shape[1] != 2 or not np.all(np.isfinite(array)):
            raise ValueError("Rectangle centers must have finite [x, y] rows.")
        centers = array
        array = np.empty((len(centers), 4), dtype=float)
        array[:, :2] = centers
        array[:, 2] = _sizes(height, len(centers), "height")
        array[:, 3] = _sizes(width, len(centers), "width")
    array.flags.writeable = False
    return array


def _colors(value: Any, count: int, name: str) -> np.ndarray:
    if count == 0 and isinstance(value, np.ndarray) and value.shape == (0, 4):
        return np.empty((0, 4), dtype=np.float32)
    colors = transform_color(value)
    if len(colors) == 1:
        source = np.asarray(value)
        if count != 1 or (source.ndim < 2 and not (source.shape == (1,) and source.dtype.kind == "U")):
            return colors[0].copy()
    if len(colors) != count:
        raise ValueError(f"{name} must be one color or contain one color per rectangle.")
    return colors.copy()


def _symbol(value: str) -> str:
    try:
        return str(SYMBOL_DICT[value])
    except KeyError as error:
        raise ValueError(f"Unknown marker symbol {value!r}.") from error


def _resize_rows(array: np.ndarray, count: int, default: Any) -> np.ndarray:
    retained = min(len(array), count)
    result = np.empty((count, *array.shape[1:]), dtype=array.dtype)
    result[:retained] = array[:retained]
    result[retained:] = default
    return result


class Rectangles(BaseLayer):
    """Display 2D rectangle outlines with optional center markers and labels.

    Pass [x, y] `centers` with `height` and `width` in data units.
    Dimensions can be scalars or arrays with one value per rectangle.
    Alternatively, pass [x, y, height, width] rows as the first argument.

    Outlines use one `outline_width` in screen pixels and accept shared or
    per-rectangle `outline_color`. Markers use Scatter symbols and accept
    shared or per-rectangle `marker_size` in screen pixels, `marker_color`,
    and `marker_symbol`. Pass one literal string per rectangle as `text`.
    Labels use a shared `text_size` in screen points (None uses the application
    setting), `text_color`, and an [x, y] `text_offset` in data units.
    """

    def __init__(
        self,
        centers: ArrayLike | None = None,
        height: ArrayLike | None = None,
        width: ArrayLike | None = None,
        *,
        show_rectangles: bool = True,
        show_markers: bool = False,
        show_text: bool = True,
        outline_width: float = 1.0,
        outline_color: Any = "white",
        marker_size: ArrayLike = _DEFAULT_MARKER_SIZE,
        marker_color: Any = "white",
        marker_symbol: str | Sequence[str] | np.ndarray = _DEFAULT_MARKER_SYMBOL,
        text: Sequence[str] | np.ndarray | None = None,
        text_size: float | None = None,
        text_color: Any = "white",
        text_offset: ArrayLike = (0, 0),
        axis_labels: Sequence[str] | None = None,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
        scale: Sequence[float] | None = None,
        translate: Sequence[float] | None = None,
        rotate: ArrayLike | None = None,
        shear: ArrayLike | None = None,
        affine: Affine | ArrayLike | None = None,
        opacity: float = 1.0,
        blending: str = "translucent",
        experimental_clipping_planes: Any = None,
        projection_mode: str = "none",
        units: Sequence[Any] | None = None,
        visible: bool = True,
    ) -> None:
        self._data = _geometry(centers, height, width)
        super().__init__(
            self._data,
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
            show_rectangles=Event,
            show_markers=Event,
            show_text=Event,
            outline_width=Event,
            outline_color=Event,
            marker_size=Event,
            marker_color=Event,
            marker_symbol=Event,
            text=Event,
            text_size=Event,
            text_color=Event,
            text_offset=Event,
        )
        self.show_rectangles = show_rectangles
        self.show_markers = show_markers
        self.show_text = show_text
        self.outline_width = outline_width
        self.outline_color = outline_color
        self.marker_size = marker_size
        self.marker_color = marker_color
        self.marker_symbol = marker_symbol
        self.text = text
        self.text_size = text_size
        self.text_color = text_color
        self.text_offset = text_offset

    @property
    def data(self) -> np.ndarray:
        """Read-only [x, y, height, width] rows. Assign new rows to update."""
        return self._data

    @data.setter
    def data(self, value: ArrayLike | None) -> None:
        self._replace_data(_geometry(value, None, None))

    @property
    def centers(self) -> np.ndarray:
        """Read-only [x, y] rectangle centers."""
        return self._data[:, :2]

    def set_data(self, centers: ArrayLike, height: ArrayLike, width: ArrayLike) -> None:
        """Replace geometry from [x, y] centers and scalar or per-row dimensions."""
        self._replace_data(_geometry(centers, height, width))

    def _replace_data(self, data: np.ndarray) -> None:
        count = len(data)
        if count != len(self._data):
            if self._outline_color.ndim == 2:
                self._outline_color = _resize_rows(self._outline_color, count, _DEFAULT_COLOR)
            if self._marker_color.ndim == 2:
                self._marker_color = _resize_rows(self._marker_color, count, _DEFAULT_COLOR)
            if isinstance(self._marker_size, np.ndarray):
                self._marker_size = _resize_rows(self._marker_size, count, _DEFAULT_MARKER_SIZE)
            if isinstance(self._marker_symbol, np.ndarray):
                self._marker_symbol = _resize_rows(self._marker_symbol, count, _DEFAULT_MARKER_SYMBOL)
            if self._text is not None:
                self._text = _resize_rows(self._text, count, "")
        self._data = data
        if not self.visible:
            self._clear_extent()
        self._emit_new_data(action_type=ActionType.CHANGED)

    @property
    def show_rectangles(self) -> bool:
        """Whether to draw the rectangle outlines."""
        return self._show_rectangles

    @show_rectangles.setter
    def show_rectangles(self, value: bool) -> None:
        self._show_rectangles = bool(value)
        self.events.show_rectangles(value=self._show_rectangles)

    @property
    def show_markers(self) -> bool:
        """Whether to mark the rectangle centers."""
        return self._show_markers

    @show_markers.setter
    def show_markers(self, value: bool) -> None:
        self._show_markers = bool(value)
        self.events.show_markers(value=self._show_markers)

    @property
    def show_text(self) -> bool:
        """Whether to draw the supplied labels."""
        return self._show_text

    @show_text.setter
    def show_text(self, value: bool) -> None:
        self._show_text = bool(value)
        self.events.show_text(value=self._show_text)

    @property
    def outline_width(self) -> float:
        """Shared outline width in screen pixels."""
        return self._outline_width

    @outline_width.setter
    def outline_width(self, value: float) -> None:
        self._outline_width = _positive(value, "outline_width")
        self.events.outline_width(value=self._outline_width)

    @property
    def outline_color(self) -> np.ndarray:
        """Shared RGBA outline color or one RGBA row per rectangle."""
        return self._outline_color

    @outline_color.setter
    def outline_color(self, value: Any) -> None:
        self._outline_color = _colors(value, len(self.data), "outline_color")
        self.events.outline_color(value=self._outline_color)

    @property
    def marker_size(self) -> float | np.ndarray:
        """Marker diameters in screen pixels."""
        return self._marker_size

    @marker_size.setter
    def marker_size(self, value: ArrayLike) -> None:
        self._marker_size = _sizes(value, len(self.data), "marker_size")
        self.events.marker_size(value=self._marker_size)

    @property
    def marker_color(self) -> np.ndarray:
        """Shared RGBA marker color or one RGBA row per rectangle."""
        return self._marker_color

    @marker_color.setter
    def marker_color(self, value: Any) -> None:
        self._marker_color = _colors(value, len(self.data), "marker_color")
        self.events.marker_color(value=self._marker_color)

    @property
    def marker_symbol(self) -> str | np.ndarray:
        """Scatter symbol name or one name per marker."""
        return self._marker_symbol

    @marker_symbol.setter
    def marker_symbol(self, value: str | Sequence[str] | np.ndarray) -> None:
        if isinstance(value, str):
            symbols = _symbol(value)
        else:
            array = np.asarray(value, dtype=str)
            if array.shape != (len(self.data),):
                raise ValueError("marker_symbol must be one symbol or contain one symbol per rectangle.")
            unique, inverse = np.unique(array, return_inverse=True)
            symbols = np.asarray([_symbol(item) for item in unique], dtype=object)[inverse]
        self._marker_symbol = symbols
        self.events.marker_symbol(value=symbols)

    @property
    def text(self) -> np.ndarray | None:
        """Literal label strings, or None when no labels are supplied."""
        return self._text

    @text.setter
    def text(self, value: Sequence[str] | np.ndarray | None) -> None:
        labels = None
        if value is not None:
            labels = np.asarray(value, dtype=object)
            if labels.shape != (len(self.data),) or not all(isinstance(label, str) for label in labels):
                raise ValueError("text must contain one label string per rectangle.")
            labels = labels.copy()
        self._text = labels
        self.events.text(value=labels)

    @property
    def text_size(self) -> float | None:
        """Font size in screen points, or None to use the application setting."""
        return self._text_size

    @text_size.setter
    def text_size(self, value: float | None) -> None:
        self._text_size = None if value is None else _positive(value, "text_size")
        self.events.text_size(value=self._text_size)

    @property
    def text_color(self) -> np.ndarray:
        """Shared RGBA label color."""
        return self._text_color

    @text_color.setter
    def text_color(self, value: Any) -> None:
        colors = transform_color(value)
        if colors.shape != (1, 4):
            raise ValueError("text_color must be one color.")
        self._text_color = colors[0].copy()
        self.events.text_color(value=self._text_color)

    @property
    def text_offset(self) -> np.ndarray:
        """Shared [x, y] label offset from the centers in data units."""
        return self._text_offset

    @text_offset.setter
    def text_offset(self, value: ArrayLike) -> None:
        offset = np.asarray(value, dtype=float)
        if offset.shape != (2,) or not np.all(np.isfinite(offset)):
            raise ValueError("text_offset must be a finite [x, y] pair.")
        self._text_offset = offset.copy()
        self.events.text_offset(value=self._text_offset)

    def _get_state(self) -> dict[str, Any]:
        state = self._get_base_state()
        state.update(
            data=self.data,
            show_rectangles=self.show_rectangles,
            show_markers=self.show_markers,
            show_text=self.show_text,
            outline_width=self.outline_width,
            outline_color=self.outline_color,
            marker_size=self.marker_size,
            marker_color=self.marker_color,
            marker_symbol=self.marker_symbol,
            text=self.text,
            text_size=self.text_size,
            text_color=self.text_color,
            text_offset=self.text_offset,
        )
        return state

    @property
    def _extent_data(self) -> np.ndarray:
        if not len(self.data):
            return np.full((2, 2), np.nan)
        half_size = self.data[:, 3:1:-1] * 0.5
        minimum = (self.centers - half_size).min(axis=0)
        maximum = (self.centers + half_size).max(axis=0)
        return np.stack((minimum[::-1], maximum[::-1]))

    def _set_view_slice(self) -> None:
        pass

    def _get_value(self, position: np.ndarray) -> None:
        return None

    def _update_thumbnail(self) -> None:
        thumbnail = np.zeros(self._thumbnail_shape)
        thumbnail[8:24, (5, 26)] = _DEFAULT_COLOR
        thumbnail[(8, 23), 5:27] = _DEFAULT_COLOR
        thumbnail[..., 3] *= self.opacity
        self.thumbnail = thumbnail
