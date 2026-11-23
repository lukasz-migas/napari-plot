"""Figure-level statistical plots using the viewer's grid cells."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from itertools import product
from math import ceil
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import numpy as np
import pandas as pd

from napari_plot.layers._grouping import LAYER_GROUP_KEY
from napari_plot.stats import categorical, distributions, relational
from napari_plot.stats._common import legend_entries, set_axis_labels
from napari_plot.stats._data import _as_frame, _resolve, long_frame, normalize_categorical
from napari_plot.stats._palette import level_colors
from napari_plot.stats._seaborn import categorical_order

if TYPE_CHECKING:
    from napari.layers import Layer

    from napari_plot.components.viewer_model import ViewerModel

_DISTRIBUTIONS = {"hist": distributions.histplot, "kde": distributions.kdeplot, "ecdf": distributions.ecdfplot}
_CATEGORICAL = {
    "bar": categorical.barplot,
    "box": categorical.boxplot,
    "boxen": categorical.boxenplot,
    "count": categorical.countplot,
    "point": categorical.pointplot,
    "strip": categorical.stripplot,
    "swarm": categorical.swarmplot,
    "violin": categorical.violinplot,
}
_RELATIONAL = {"scatter": relational.scatterplot, "line": relational.lineplot, "reg": relational.regplot}
_BIVARIATE = {**_RELATIONAL, "hist": distributions.histplot, "kde": distributions.kdeplot}


class FacetGrid:
    """Draw a statistical plot in each subset of a table, on one plot viewer.

    ``row`` and ``col`` name the variables used to split the data. ``col_wrap`` wraps a single column variable
    across multiple rows. ``sharex`` and ``sharey`` determine whether the respective limits are linked.
    Map a napari-plot statistical function with ``map_dataframe`` and access the created layers via ``layers``.
    """

    def __init__(
        self,
        viewer: ViewerModel,
        data: Any = None,
        *,
        row: Any = None,
        col: Any = None,
        row_order: Sequence[Any] | None = None,
        col_order: Sequence[Any] | None = None,
        col_wrap: int | None = None,
        sharex: bool = True,
        sharey: bool = True,
    ) -> None:
        if col_wrap is not None and (col is None or row is not None or col_wrap < 1):
            raise ValueError("col_wrap needs a positive value and a column facet without a row facet.")
        self.viewer = viewer
        self.data = data
        self.sharex = sharex
        self.sharey = sharey
        self.layers: list[Layer] = []
        self._group_prefix = f"facet-{uuid4()}"
        self._frame = _as_frame(data)
        row_values, row_label = _resolve(self._frame, row)
        col_values, col_label = _resolve(self._frame, col)
        self._panels: dict[tuple[int, int], tuple[Any, str]] = {}
        self._panel_indices: dict[tuple[int, int], np.ndarray] = {}
        if row_values is None and col_values is None:
            self._shape = (1, 1)
            self._panels[(0, 0)] = (data, "")
        else:
            if self._frame is None:
                raise ValueError("Row and column facets need tabular data.")
            rows = [None] if row_values is None else categorical_order(row_values, row_order)
            cols = [None] if col_values is None else categorical_order(col_values, col_order)
            if not rows or not cols:
                raise ValueError("Facet variables must contain at least one level.")
            width = min(col_wrap or len(cols), len(cols))
            self._shape = (len(rows) if col_wrap is None else ceil(len(cols) / width), width)
            for (i, row_value), (j, col_value) in product(enumerate(rows), enumerate(cols)):
                mask = pd.Series(True, index=range(len(self._frame)))
                title = []
                if row_values is not None:
                    mask &= row_values.eq(row_value).fillna(False)
                    title.append(f"{row_label or 'row'} = {row_value}")
                if col_values is not None:
                    mask &= col_values.eq(col_value).fillna(False)
                    title.append(f"{col_label or 'col'} = {col_value}")
                position = (i, j) if col_wrap is None else divmod(j, width)
                indices = np.flatnonzero(mask)
                self._panel_indices[position] = indices
                self._panels[position] = (self._frame.iloc[indices], ", ".join(title))

    def facet_data(self) -> Iterator[tuple[tuple[int, int], Any]]:
        """Iterate over zero-based grid positions and their data subsets."""
        for position, (data, _title) in self._panels.items():
            yield position, data

    def _group(self, position: tuple[int, int]) -> str:
        return f"{self._group_prefix}-{position[0]}-{position[1]}"

    def _configure(self) -> None:
        grid = self.viewer.canvas.grid
        grid.shape = self._shape
        grid.sharex = self.sharex
        grid.sharey = self.sharey
        for position, (_, title) in self._panels.items():
            cell = grid.cell(*position)
            cell.group = self._group(position)
            if title and cell.x_label is None:
                cell.x_label = title
        grid.group_by_metadata = True
        grid.enabled = True

    def map_dataframe(self, func: Callable[..., Any], **kwargs: Any) -> FacetGrid:
        """Call a napari-plot function with each subset as its ``data`` argument."""

        def plot_for(position: tuple[int, int]) -> tuple[Callable[..., Any], dict[str, Any]]:
            indices = self._panel_indices.get(position)
            options = dict(kwargs)
            if indices is not None:
                for key in ("x", "y", "hue", "size", "style", "weights"):
                    value = options.get(key)
                    if value is not None and not isinstance(value, str) and np.ndim(value) == 1:
                        options[key] = (
                            value.iloc[indices] if isinstance(value, pd.Series) else np.asarray(value)[indices]
                        )
            return func, options

        return self._map(plot_for)

    def _map(self, method: Callable[[tuple[int, int]], tuple[Callable[..., Any], dict[str, Any]]]) -> FacetGrid:
        from napari_plot.components.viewer_model import ViewerModel

        first_legend = []
        prepared = []
        for position, (data, title) in self._panels.items():
            if isinstance(data, pd.DataFrame) and data.empty:
                continue
            plot, options = method(position)
            stage = ViewerModel()
            plot(stage, data=data, **options)
            axis_settings = {
                "x_label": f"{stage.axis.x_label} ({title})" if title else stage.axis.x_label,
                "y_label": stage.axis.y_label,
                "x_categories": stage.axis.x_categories,
                "y_categories": stage.axis.y_categories,
                "x_scale": stage.axis.x_scale,
                "y_scale": stage.axis.y_scale,
            }
            if stage.legend.entries and not first_legend:
                first_legend = [entry.model_dump() for entry in stage.legend.entries]
            layers = list(stage.layers)
            for layer in layers:
                overlays = dict(layer._overlays)
                stage.layers.remove(layer)
                layer._overlays.update(overlays)
                layer.metadata = {**layer.metadata, LAYER_GROUP_KEY: self._group(position)}
            prepared.append((position, axis_settings, layers))
        self._configure()
        for position, axis_settings, layers in prepared:
            self.viewer.canvas.grid.cell(*position).update(axis_settings)
            for layer in layers:
                self.viewer.add_layer(layer)
                self.layers.append(layer)
        if first_legend:
            self.viewer.set_legend(first_legend)
        self.viewer.reset_view()
        return self

    def set_axis_labels(self, x_var: str | None = None, y_var: str | None = None) -> FacetGrid:
        """Set the displayed x and/or y labels in every facet."""
        for position in self._panels:
            cell = self.viewer.canvas.grid.cell(*position)
            if x_var is not None:
                cell.x_label = x_var
            if y_var is not None:
                cell.y_label = y_var
        return self


def _select_kind(plots: dict[str, Callable], kind: str) -> Callable:
    if kind not in plots:
        raise ValueError(f"Unknown {kind!r} plot kind. Choose from {', '.join(plots)}.")
    return plots[kind]


def _hue_options(data: Any, hue: Any, options: dict[str, Any], *, continuous: bool = False) -> dict[str, Any]:
    """Use a common hue mapping for every subset."""
    values, _ = _resolve(_as_frame(data), hue)
    if values is None or "hue_order" in options or "hue_norm" in options:
        return options
    if continuous and relational._is_numeric(values) and not isinstance(options.get("palette"), dict | list):
        return {**options, "hue_norm": (float(values.min()), float(values.max()))}
    return {**options, "hue_order": categorical_order(values)}


def displot(
    viewer: ViewerModel,
    data: Any = None,
    *,
    x: Any = None,
    y: Any = None,
    hue: Any = None,
    kind: str = "hist",
    facet_kws: dict[str, Any] | None = None,
    row: Any = None,
    col: Any = None,
    col_wrap: int | None = None,
    row_order: Sequence[Any] | None = None,
    col_order: Sequence[Any] | None = None,
    **kwargs: Any,
) -> FacetGrid:
    """Draw histograms, KDEs, or ECDFs across data facets."""
    plot = _select_kind(_DISTRIBUTIONS, kind)
    grid = FacetGrid(
        viewer, data, row=row, col=col, col_wrap=col_wrap, row_order=row_order, col_order=col_order, **(facet_kws or {})
    )
    return grid.map_dataframe(plot, x=x, y=y, hue=hue, **_hue_options(data, hue, kwargs))


def catplot(
    viewer: ViewerModel,
    data: Any = None,
    *,
    x: Any = None,
    y: Any = None,
    hue: Any = None,
    kind: str = "strip",
    facet_kws: dict[str, Any] | None = None,
    row: Any = None,
    col: Any = None,
    col_wrap: int | None = None,
    row_order: Sequence[Any] | None = None,
    col_order: Sequence[Any] | None = None,
    **kwargs: Any,
) -> FacetGrid:
    """Draw a categorical plot per subset with consistent category and hue levels."""
    plot = _select_kind(_CATEGORICAL, kind)
    if "order" not in kwargs and (x is not None or y is not None):
        if kind == "count":
            values, _ = _resolve(_as_frame(data), x if x is not None else y)
            kwargs["order"] = categorical_order(values)
        else:
            kwargs["order"] = normalize_categorical(data, x=x, y=y, orient=kwargs.get("orient")).categories
    grid = FacetGrid(
        viewer, data, row=row, col=col, col_wrap=col_wrap, row_order=row_order, col_order=col_order, **(facet_kws or {})
    )
    return grid.map_dataframe(plot, x=x, y=y, hue=hue, **_hue_options(data, hue, kwargs))


def lmplot(
    viewer: ViewerModel,
    data: Any = None,
    *,
    x: Any = None,
    y: Any = None,
    hue: Any = None,
    hue_order: Sequence[Any] | None = None,
    palette: Any = None,
    legend: bool = True,
    row: Any = None,
    col: Any = None,
    col_wrap: int | None = None,
    row_order: Sequence[Any] | None = None,
    col_order: Sequence[Any] | None = None,
    facet_kws: dict[str, Any] | None = None,
    **kwargs: Any,
) -> FacetGrid:
    """Fit and display a regression in each subset of the data."""
    grid = FacetGrid(
        viewer, data, row=row, col=col, col_wrap=col_wrap, row_order=row_order, col_order=col_order, **(facet_kws or {})
    )
    if hue is None:
        return grid.map_dataframe(relational.regplot, x=x, y=y, **kwargs)
    hue_values, _ = _resolve(_as_frame(data), hue)
    colors = level_colors(categorical_order(hue_values, hue_order), palette, kwargs.pop("color", None))

    def regression(stage: ViewerModel, *, data: Any, x: Any, y: Any, hue: Any, **options: Any) -> None:
        frame, labels = long_frame(data, x=x, y=y, hue=hue, dropna=("x", "y", "hue"))
        for level, color in colors.items():
            group = frame[frame["hue"].eq(level)]
            if not group.empty:
                relational.regplot(stage, group, x="x", y="y", color=color, **options)
        set_axis_labels(stage, labels.get("x"), labels.get("y"))
        if legend:
            stage.set_legend(legend_entries(colors))

    return grid.map_dataframe(regression, x=x, y=y, hue=hue, **kwargs)


def pairplot(
    viewer: ViewerModel,
    data: Any,
    *,
    vars: Sequence[str] | None = None,  # noqa: A002
    x_vars: Sequence[str] | None = None,
    y_vars: Sequence[str] | None = None,
    hue: Any = None,
    kind: str = "scatter",
    diag_kind: str = "hist",
    corner: bool = False,
    plot_kws: dict[str, Any] | None = None,
    diag_kws: dict[str, Any] | None = None,
) -> FacetGrid:
    """Draw pairwise plots for numeric columns and distributions for matching columns."""
    frame = _as_frame(data)
    if frame is None:
        raise ValueError("pairplot needs tabular data.")
    columns = list(vars) if vars is not None else list(frame.select_dtypes("number").columns)
    if vars is None and isinstance(hue, str):
        columns = [column for column in columns if column != hue]
    x_columns = list(x_vars) if x_vars is not None else columns
    y_columns = list(y_vars) if y_vars is not None else columns
    if not x_columns or not y_columns:
        raise ValueError("pairplot needs at least one x and one y variable.")
    off_diagonal = _select_kind(_BIVARIATE, kind)
    diagonal = _select_kind(
        _DISTRIBUTIONS, ("kde" if hue is not None else "hist") if diag_kind == "auto" else diag_kind
    )
    plot_kws = plot_kws or {}
    if hue is not None and kind == "reg":
        raise ValueError("pairplot does not support hue with kind='reg'.")
    if hue is not None:
        plot_kws = {**_hue_options(frame, hue, plot_kws, continuous=kind == "scatter"), "hue": hue}
    diag_kws = {**_hue_options(frame, hue, diag_kws or {}), "hue": hue}
    grid = FacetGrid(viewer, frame, sharex=False, sharey=False)
    grid._shape = (len(y_columns), len(x_columns))
    grid._panels = {
        (i, j): (frame, "") for i, j in product(range(len(y_columns)), range(len(x_columns))) if not corner or j <= i
    }

    def plot_for(position: tuple[int, int]) -> tuple[Callable[..., Any], dict[str, Any]]:
        row, column = position
        x, y = x_columns[column], y_columns[row]
        if x == y:
            return diagonal, {**diag_kws, "x": x}
        return off_diagonal, {**plot_kws, "x": x, "y": y}

    return grid._map(plot_for)


def jointplot(
    viewer: ViewerModel,
    data: Any = None,
    *,
    x: Any,
    y: Any,
    hue: Any = None,
    kind: str = "scatter",
    joint_kws: dict[str, Any] | None = None,
    marginal_kws: dict[str, Any] | None = None,
) -> FacetGrid:
    """Draw a bivariate plot and its two marginal distributions."""
    joint = _select_kind(_BIVARIATE, kind)
    joint_kws = joint_kws or {}
    if hue is not None and kind == "reg":
        raise ValueError("jointplot does not support hue with kind='reg'.")
    if hue is not None:
        joint_kws = {**_hue_options(data, hue, joint_kws, continuous=kind == "scatter"), "hue": hue}
    marginal_kws = {**_hue_options(data, hue, marginal_kws or {}), "hue": hue}
    grid = FacetGrid(viewer, data, sharex=False, sharey=False)
    grid._shape = (2, 2)
    grid._panels = {(0, 0): (data, ""), (1, 0): (data, ""), (1, 1): (data, "")}
    margin = distributions.kdeplot if kind == "kde" else distributions.histplot
    plots = {
        (0, 0): (margin, {**marginal_kws, "x": x}),
        (1, 0): (joint, {**joint_kws, "x": x, "y": y}),
        (1, 1): (margin, {**marginal_kws, "y": y}),
    }
    grid._map(plots.__getitem__)
    for axis, positions in (("x", ((0, 0), (1, 0))), ("y", ((1, 0), (1, 1)))):
        groups = {grid._group(position) for position in positions}
        layers = [layer for layer in grid.layers if layer.metadata[LAYER_GROUP_KEY] in groups]
        extent = viewer._get_rect_extent(layers=layers)
        limits = extent[:2] if axis == "x" else extent[2:]
        if limits[0] < limits[1]:
            for position in positions:
                setattr(viewer.canvas.grid.cell(*position), f"{axis}lim", limits)
    return grid
