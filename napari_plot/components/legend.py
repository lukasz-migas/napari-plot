"""Canvas legend overlay models and entry helpers."""

from __future__ import annotations

import collections.abc as cabc
import typing as ty
from contextlib import suppress

import numpy as np
from napari.components._viewer_constants import CanvasPosition
from napari.components.overlays import CanvasOverlay
from napari.layers import Points
from napari.layers.base import Layer
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import EventedModel
from napari.utils.events.custom_types import Array
from pydantic import field_validator

from napari_plot.layers import Bar, Centroids, InfLine, Line, MultiLine, Region, Scatter, Text

ColorLike = ty.Any

EMPTY_LABEL_ERROR = "Legend entry labels must not be empty."
LEGEND_ENTRY_ERROR = "Legend entries must be LegendEntry instances or mappings."
LEGEND_ENTRIES_ERROR = "Legend entries must be one entry or a sequence of entries."
LEGEND_COLOR_ERROR = "Legend colors must resolve to a single color."
LEGEND_SIZE_ERROR = "Legend sizes and spacing must be positive."
LEGEND_PADDING_ERROR = "Legend padding must be non-negative."
LEGEND_BORDER_ERROR = "Legend border width must be non-negative."
LABEL_PROPERTY_ERROR = "Points legend label property must exist on the layer."

DEFAULT_LEGEND_TEXT_COLOR = (1.0, 1.0, 1.0, 1.0)
DEFAULT_LEGEND_BACKGROUND_COLOR = (0.0, 0.0, 0.0, 0.65)
DEFAULT_LEGEND_BORDER_COLOR = (1.0, 1.0, 1.0, 0.8)

SYMBOL_ALIASES = {
    "o": "disc",
    "*": "star",
    "+": "cross",
    "-": "hbar",
    "->": "tailed_arrow",
    ">": "arrow",
    "^": "triangle_up",
    "v": "triangle_down",
    "s": "square",
    "|": "vbar",
}


def _coerce_single_color(value: ColorLike) -> np.ndarray:
    colors = transform_color(value)
    if len(colors) != 1:
        raise ValueError(LEGEND_COLOR_ERROR)
    return np.asarray(colors[0], dtype=float)


def _coerce_marker(value: ty.Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "value"):
        value = value.value
    marker = str(value)
    if not marker or marker.lower() in {"none", "null"}:
        return None
    return SYMBOL_ALIASES.get(marker, marker)


class LegendEntry(EventedModel):
    """One label and optional style swatch in a legend."""

    label: str
    marker: str | None = None
    color: Array[float, (4,)] | None = None
    colormap: str | None = None
    layer_name: str | None = None

    @field_validator("label", mode="before")
    @classmethod
    def _coerce_label(cls, value: ty.Any) -> str:
        label = str(value)
        if not label:
            raise ValueError(EMPTY_LABEL_ERROR)
        return label

    @field_validator("marker", mode="before")
    @classmethod
    def _validate_marker(cls, value: ty.Any) -> str | None:
        return _coerce_marker(value)

    @field_validator("color", mode="before")
    @classmethod
    def _validate_color(cls, value: ColorLike | None) -> np.ndarray | None:
        return None if value is None else _coerce_single_color(value)

    @field_validator("colormap", mode="before")
    @classmethod
    def _validate_colormap(cls, value: ty.Any) -> str | None:
        if value is None:
            return None
        colormap = str(value)
        return colormap or None


LegendEntryLike = LegendEntry | ty.Mapping[str, ty.Any]
LegendInput = LegendEntryLike | ty.Sequence[LegendEntryLike]


def _coerce_entry(value: ty.Any) -> LegendEntry:
    if isinstance(value, LegendEntry):
        return value
    if isinstance(value, cabc.Mapping):
        return LegendEntry(**value)
    raise TypeError(LEGEND_ENTRY_ERROR)


def normalize_legend_entries(entries: LegendInput | LegendEntry | None) -> tuple[LegendEntry, ...]:
    """Normalize legend input into immutable entry models."""
    if entries is None:
        return ()
    if isinstance(entries, (LegendEntry, cabc.Mapping)):
        return (_coerce_entry(entries),)
    if isinstance(entries, cabc.Sequence) and not isinstance(entries, str):
        return tuple(_coerce_entry(entry) for entry in entries)
    raise TypeError(LEGEND_ENTRIES_ERROR)


def _feature_values(layer: Points, name: str) -> ty.Any:
    if name in layer.properties:
        return np.asarray(layer.properties[name])
    features = getattr(layer, "features", None)
    if features is not None and name in features:
        return np.asarray(features[name])
    raise KeyError(name)


def _optional_feature_values(layer: Points, name: str | None) -> ty.Any:
    if name is None or name.lower() == "none":
        return None
    if name == "symbol":
        return np.asarray(layer.symbol)
    if name == "face":
        return np.asarray(layer.face_color)
    if name == "border":
        return np.asarray(layer.border_color)
    with suppress(KeyError):
        return _feature_values(layer, name)
    return None


def _value_at(values: ty.Any, index: int) -> ty.Any:
    if values is None:
        return None
    try:
        if np.ndim(values) == 0:
            return values
        return values[index]
    except (IndexError, TypeError):
        return values


def legend_entries_from_points(
    layer: Points,
    *,
    label_property: str = "label",
    color_source: str = "face",
    marker_source: str = "symbol",
    group_by_style: bool = True,
) -> tuple[LegendEntry, ...]:
    """Create deduplicated legend entries from a Points layer."""
    try:
        labels = _feature_values(layer, label_property)
    except KeyError as error:
        raise ValueError(LABEL_PROPERTY_ERROR) from error

    colors = _optional_feature_values(layer, color_source)
    markers = _optional_feature_values(layer, marker_source)
    entries: list[LegendEntry] = []
    seen: set[tuple[ty.Any, ...]] = set()
    for index, label in enumerate(labels):
        label_text = str(label)
        marker = _value_at(markers, index)
        color = _value_at(colors, index)
        key: tuple[ty.Any, ...] = (label_text,)
        if group_by_style:
            marker_key = _coerce_marker(marker)
            color_key = None if color is None else tuple(np.round(_coerce_single_color(color), 6))
            key = label_text, marker_key, color_key
        if key in seen:
            continue
        seen.add(key)
        entries.append(LegendEntry(label=label_text, marker=marker, color=color, layer_name=layer.name))
    return tuple(entries)


def _layer_has_data(layer: Layer) -> bool:
    data = getattr(layer, "data", None)
    if data is None:
        return False
    with suppress(TypeError):
        return len(data) > 0
    return np.asarray(data).size > 0


def _first_value(value: ty.Any) -> ty.Any:
    if value is None:
        return None
    array = np.asarray(value, dtype=object)
    if array.ndim == 0:
        return array.item()
    return None if array.size == 0 else array.flat[0]


def _first_color(value: ty.Any) -> ty.Any:
    if value is None:
        return None
    array = np.asarray(value)
    if array.size == 0:
        return None
    return array if array.ndim <= 1 else array[0]


def _orientation_marker(layer: ty.Any, *, horizontal: str = "hbar", vertical: str = "vbar") -> str:
    orientation = _first_value(getattr(layer, "orientation", None))
    return vertical if str(orientation) == "vertical" else horizontal


def legend_entry_from_layer(layer: Layer) -> LegendEntry | None:
    """Create a legend entry from a visible, supported plot layer."""
    if not layer.visible or not _layer_has_data(layer):
        return None
    if isinstance(layer, Line):
        return LegendEntry(label=layer.name, marker="hbar", color=layer.color, layer_name=layer.name)
    if isinstance(layer, (MultiLine, Text, Region, InfLine, Centroids)):
        color = _first_color(getattr(layer, "color", None))
        marker = _orientation_marker(layer) if isinstance(layer, (Region, InfLine, Centroids)) else "hbar"
        return LegendEntry(label=layer.name, marker=marker, color=color, layer_name=layer.name)
    if isinstance(layer, Bar):
        return LegendEntry(
            label=layer.name,
            marker="square",
            color=_first_color(layer.fill_color),
            layer_name=layer.name,
        )
    if isinstance(layer, (Scatter, Points)):
        color = _first_color(getattr(layer, "face_color", None))
        if color is None:
            color = _first_color(getattr(layer, "border_color", None))
        marker = _first_value(getattr(layer, "symbol", None))
        return LegendEntry(label=layer.name, marker=marker, color=color, layer_name=layer.name)
    return None


def legend_entries_from_layers(layers: ty.Iterable[Layer]) -> tuple[LegendEntry, ...]:
    """Create legend entries in layer-list order."""
    return tuple(entry for layer in layers if (entry := legend_entry_from_layer(layer)) is not None)


class LegendOverlay(CanvasOverlay):
    """Canvas-space legend rendered above plot layers."""

    box: bool = False
    position: CanvasPosition = CanvasPosition.TOP_RIGHT
    entries: tuple[LegendEntry, ...] = ()
    text_color: Array[float, (4,)] = DEFAULT_LEGEND_TEXT_COLOR
    font_size: float = 10.0
    marker_size: float = 10.0
    row_spacing: float = 4.0
    padding: float = 6.0
    background_color: Array[float, (4,)] = DEFAULT_LEGEND_BACKGROUND_COLOR
    border_color: Array[float, (4,)] = DEFAULT_LEGEND_BORDER_COLOR
    border_width: float = 1.0
    source_layer: str | None = None
    label_property: str = "label"
    color_source: str = "face"
    marker_source: str = "symbol"
    group_by_style: bool = True
    sync_with_source: bool = True

    @field_validator("entries", mode="before")
    @classmethod
    def _coerce_entries(cls, value: ty.Any) -> tuple[LegendEntry, ...]:
        return normalize_legend_entries(value)

    @field_validator("text_color", "background_color", "border_color", mode="before")
    @classmethod
    def _coerce_color(cls, value: ColorLike) -> np.ndarray:
        return _coerce_single_color(value)

    @field_validator("font_size", "marker_size", "row_spacing", mode="before")
    @classmethod
    def _coerce_positive_number(cls, value: float) -> float:
        number = float(value)
        if number <= 0:
            raise ValueError(LEGEND_SIZE_ERROR)
        return number

    @field_validator("padding", mode="before")
    @classmethod
    def _coerce_padding(cls, value: float) -> float:
        padding = float(value)
        if padding < 0:
            raise ValueError(LEGEND_PADDING_ERROR)
        return padding

    @field_validator("border_width", mode="before")
    @classmethod
    def _coerce_border_width(cls, value: float) -> float:
        width = float(value)
        if width < 0:
            raise ValueError(LEGEND_BORDER_ERROR)
        return width

    def set_entries(self, entries: LegendInput | LegendEntry | None) -> None:
        """Replace the legend rows."""
        self.entries = normalize_legend_entries(entries)


# Backward-compatible name introduced with the first napari-plot legend API.
Legend = LegendOverlay

__all__ = [
    "ColorLike",
    "Legend",
    "LegendEntry",
    "LegendEntryLike",
    "LegendInput",
    "LegendOverlay",
    "legend_entries_from_layers",
    "legend_entries_from_points",
    "legend_entry_from_layer",
    "normalize_legend_entries",
]
