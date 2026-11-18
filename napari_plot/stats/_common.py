"""Layout and layer-building helpers shared by every statistical plot.

Plots are written once in ``(position, value)`` space, where ``position`` runs along the categorical (or
independent) axis. ``orient`` decides whether that maps to ``(x, y)`` (``"v"``) or ``(y, x)`` (``"h"``).
"""

from __future__ import annotations

import typing as ty
from collections.abc import Iterable, Mapping, Sequence

import numpy as np

from napari_plot.stats._data import CategoricalData, Orient

if ty.TYPE_CHECKING:
    from napari.layers import Layer

    from napari_plot.components.viewer_model import ViewerModel
    from napari_plot.layers import MultiLine, Scatter


def dodge_offsets(n_hue: int, width: float, dodge: bool) -> tuple[np.ndarray, float]:
    """Return per-hue position offsets and the width available to each element."""
    if not dodge or n_hue <= 1:
        return np.zeros(max(n_hue, 1)), width
    element = width / n_hue
    return (np.arange(n_hue) - (n_hue - 1) / 2) * element, element


def iter_cells(
    data: CategoricalData, width: float, dodge: bool
) -> ty.Iterator[tuple[ty.Any, list[tuple[int, float, np.ndarray]], float]]:
    """Yield ``(hue_level, [(category_index, position, values), ...], element_width)`` per hue level."""
    levels = data.hue_levels or [None]
    offsets, element = dodge_offsets(len(levels), width, dodge and data.hue_levels is not None)
    for hue_index, level in enumerate(levels):
        cells = []
        for index, category in enumerate(data.categories):
            values = data.values(category, level)
            if len(values):
                cells.append((index, index + offsets[hue_index], values))
        yield level, cells, element


def to_xy(position: ty.Any, value: ty.Any, orient: Orient) -> tuple[np.ndarray, np.ndarray]:
    """Map ``(position, value)`` coordinates to ``(x, y)``."""
    position, value = np.asarray(position, dtype=float), np.asarray(value, dtype=float)
    return (position, value) if orient == "v" else (value, position)


def bar_orientation(orient: Orient) -> str:
    """Return the ``Bar`` orientation whose bars grow along the value axis."""
    return "vertical" if orient == "v" else "horizontal"


def areas_orientation(orient: Orient) -> str:
    """Return the ``Areas`` orientation whose ``t`` coordinate runs along the value axis."""
    return "horizontal" if orient == "v" else "vertical"


def add_segments(
    viewer: ViewerModel,
    segments: ty.Any,
    orient: Orient,
    *,
    color: ty.Any,
    width: float,
    name: str,
) -> MultiLine | None:
    """Add (position, value) segments or polylines (each an ``(M, 2)`` array) as one MultiLine layer."""
    lines = [np.asarray(line, dtype=float) for line in segments]
    if not lines:
        return None
    xs, ys = [], []
    for line in lines:
        x, y = to_xy(line[:, 0], line[:, 1], orient)
        xs.append(x)
        ys.append(y)
    color = np.asarray(color, dtype=float)
    if color.ndim == 2 and len(color) == 1:
        color = color[0]
    if color.ndim == 1:
        color = np.broadcast_to(color, (len(lines), 4)).copy()
    return viewer.add_multi_line({"xs": xs, "ys": ys}, color=color, width=width, name=name)


def add_points(
    viewer: ViewerModel,
    position: ty.Any,
    value: ty.Any,
    orient: Orient,
    *,
    face_color: ty.Any,
    size: ty.Any,
    name: str,
    symbol: ty.Any = "disc",
    border_color: ty.Any = "transparent",
    **kwargs: ty.Any,
) -> Scatter | None:
    """Add (position, value) points as a Scatter layer sized in screen pixels."""
    x, y = to_xy(position, value, orient)
    if x.size == 0:
        return None
    return viewer.add_scatter(
        np.column_stack((y, x)),
        face_color=face_color,
        size=size,
        symbol=symbol,
        border_color=border_color,
        scaling=False,
        name=name,
        **kwargs,
    )


def set_axis_labels(viewer: ViewerModel, x_label: str | None, y_label: str | None) -> None:
    """Set axis labels that are known (column names)."""
    if x_label:
        viewer.axis.x_label = x_label
    if y_label:
        viewer.axis.y_label = y_label


def apply_categorical_axis(viewer: ViewerModel, data: CategoricalData) -> None:
    """Label the categorical axis with category names and set axis titles."""
    if data.orient == "v":
        viewer.axis.x_categories = data.labels
        set_axis_labels(viewer, data.category_label, data.value_label)
    else:
        viewer.axis.y_categories = data.labels
        set_axis_labels(viewer, data.value_label, data.category_label)


def legend_entries(colors: Mapping[ty.Any, np.ndarray], marker: str = "square") -> list[dict]:
    """Return legend entries for colored levels."""
    return [{"label": str(level), "marker": marker, "color": color} for level, color in colors.items()]


def fit_view(
    viewer: ViewerModel, include: tuple[float, float, float, float] | None = None, margin: float = 0.05
) -> None:
    """Fit the camera to all layers (and ``include`` bounds) with a relative ``margin`` so edges are not clipped."""
    xmin, xmax, ymin, ymax = viewer._get_rect_extent()
    if include is not None:
        xmin, xmax = min(xmin, include[0]), max(xmax, include[1])
        ymin, ymax = min(ymin, include[2]), max(ymax, include[3])
    if not np.all(np.isfinite([xmin, xmax, ymin, ymax])):
        viewer.reset_view()
        return
    x_pad, y_pad = (xmax - xmin) * margin, (ymax - ymin) * margin
    viewer.camera.set_rect(xmin - x_pad, xmax + x_pad, ymin - y_pad, ymax + y_pad)


def finish(
    viewer: ViewerModel, layers: Iterable[Layer | None], entries: Sequence[dict] | None = None, legend: bool = True
) -> list[Layer]:
    """Show the legend (when there is one) and fit the view; return the created layers."""
    created = [layer for layer in layers if layer is not None]
    if legend and entries:
        viewer.set_legend(list(entries))
    fit_view(viewer)
    return created
