"""Figure-level statistical plots using the viewer's grid cells."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from inspect import signature
from itertools import product
from math import ceil
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import numpy as np
import pandas as pd

from napari_plot.components.joint_grid import JointGrid
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
        grid.joint = False
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

    def _map(
        self,
        method: Callable[[tuple[int, int]], tuple[Callable[..., Any], dict[str, Any]]],
        positions: set[tuple[int, int]] | None = None,
        *,
        merge_legends: bool = False,
    ) -> FacetGrid:
        from napari_plot.components.viewer_model import ViewerModel

        first_legend = []
        prepared = []
        for position, (data, title) in self._panels.items():
            if positions is not None and position not in positions:
                continue
            if isinstance(data, pd.DataFrame) and data.empty:
                continue
            plot, options = method(position)
            stage = ViewerModel()
            default_labels = (stage.axis.x_label, stage.axis.y_label)
            plot(stage, data=data, **options)
            axis_settings = {
                "x_label": f"{stage.axis.x_label} ({title})" if title else stage.axis.x_label,
                "y_label": stage.axis.y_label,
                "x_categories": stage.axis.x_categories,
                "y_categories": stage.axis.y_categories,
                "x_scale": stage.axis.x_scale,
                "y_scale": stage.axis.y_scale,
            }
            self._adjust_axis_settings(position, axis_settings, default_labels)
            if stage.legend.entries and (merge_legends or not first_legend):
                labels = {entry["label"] for entry in first_legend}
                first_legend.extend(entry.model_dump() for entry in stage.legend.entries if entry.label not in labels)
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

    def _adjust_axis_settings(
        self, position: tuple[int, int], settings: dict[str, Any], default_labels: tuple[str, str]
    ) -> None:
        pass

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


class PairGrid(FacetGrid):
    """Map callbacks across pairs of table columns using a staging viewer.

    Callbacks receive ``data``, ``x`` and ``y``. Diagonal callbacks receive
    ``data`` and ``x`` only. Variable names must be strings.
    """

    def __init__(
        self,
        viewer: ViewerModel,
        data: Any,
        *,
        vars: Sequence[str] | None = None,  # noqa: A002
        x_vars: Sequence[str] | None = None,
        y_vars: Sequence[str] | None = None,
        hue: Any = None,
        corner: bool = False,
    ) -> None:
        frame = _as_frame(data)
        if frame is None:
            raise ValueError("PairGrid needs tabular data.")
        columns = list(vars) if vars is not None else list(frame.select_dtypes("number").columns)
        if vars is None and isinstance(hue, str):
            columns = [column for column in columns if column != hue]
        self.x_vars = list(x_vars) if x_vars is not None else columns.copy()
        self.y_vars = list(y_vars) if y_vars is not None else columns.copy()
        if not self.x_vars or not self.y_vars:
            raise ValueError("PairGrid needs at least one x and one y variable.")
        for column in [*self.x_vars, *self.y_vars]:
            if not isinstance(column, str):
                raise TypeError("PairGrid variable names must be strings.")
            if column not in frame.columns:
                raise ValueError(f"Unknown column {column!r}.")
        if isinstance(hue, str) and hue not in frame.columns:
            raise ValueError(f"Unknown column {hue!r}.")
        self.hue = hue
        super().__init__(viewer, frame, sharex=False, sharey=False)
        self._shape = (len(self.y_vars), len(self.x_vars))
        self._panels = {
            (i, j): (frame, "")
            for i, j in product(range(len(self.y_vars)), range(len(self.x_vars)))
            if not corner or j <= i
        }
        self._active = False

    def _configure(self) -> None:
        grid = self.viewer.canvas.grid
        if not self._active:
            for cell in grid.cells:
                if cell.group is not None:
                    cell.group = None
        super()._configure()
        for i, j in self._panels:
            cell = grid.cell(i, j)
            if cell.x_label is None:
                cell.x_label = str(self.x_vars[j])
            if cell.y_label is None:
                cell.y_label = str(self.y_vars[i])
        self._active = True

    def _adjust_axis_settings(
        self, position: tuple[int, int], settings: dict[str, Any], default_labels: tuple[str, str]
    ) -> None:
        i, j = position
        if not settings["x_label"] or settings["x_label"] == default_labels[0]:
            settings["x_label"] = str(self.x_vars[j])
        if not settings["y_label"] or settings["y_label"] == default_labels[1]:
            settings["y_label"] = str(self.y_vars[i])

    def _map_region(self, func: Callable[..., Any], region: str, kwargs: dict[str, Any]) -> PairGrid:
        positions = set()
        for i, j in self._panels:
            diagonal = self.x_vars[j] == self.y_vars[i]
            if (
                region == "all"
                or (region == "diag" and diagonal)
                or (region == "offdiag" and not diagonal)
                or (region == "upper" and not diagonal and j > i)
                or (region == "lower" and not diagonal and i > j)
            ):
                positions.add((i, j))
        if not positions:
            return self
        options = dict(kwargs)
        if region == "diag":
            options.pop("y", None)
        hue = options.get("hue", self.hue)
        if hue is not None or "hue" in options:
            parameters = signature(func).parameters
            accepts_hue = "hue" in parameters or any(p.kind == p.VAR_KEYWORD for p in parameters.values())
            if accepts_hue:
                options.setdefault("hue", hue)
            elif hue is None:
                options.pop("hue", None)
        if hue is not None and any(
            func is plot for plot in (*_BIVARIATE.values(), *_DISTRIBUTIONS.values(), *_CATEGORICAL.values())
        ):
            options = _hue_options(self._frame, hue, options, continuous=func is relational.scatterplot)
            if (
                options.get("hue_order") is not None
                and options.get("hue_norm") is None
                and not isinstance(options.get("palette"), dict)
            ):
                options["palette"] = level_colors(options["hue_order"], options.get("palette"), options.get("color"))

        def plot_for(position: tuple[int, int]) -> tuple[Callable[..., Any], dict[str, Any]]:
            i, j = position
            arguments = {**options, "x": self.x_vars[j]}
            if region != "diag":
                arguments["y"] = self.y_vars[i]
            return func, arguments

        self._map(plot_for, positions, merge_legends=True)
        return self

    def map(self, func: Callable[..., Any], **kwargs: Any) -> PairGrid:
        """Map a bivariate function to every available cell."""
        return self._map_region(func, "all", kwargs)

    def map_upper(self, func: Callable[..., Any], **kwargs: Any) -> PairGrid:
        """Map a function above the diagonal."""
        return self._map_region(func, "upper", kwargs)

    def map_lower(self, func: Callable[..., Any], **kwargs: Any) -> PairGrid:
        """Map a function below the diagonal."""
        return self._map_region(func, "lower", kwargs)

    def map_offdiag(self, func: Callable[..., Any], **kwargs: Any) -> PairGrid:
        """Map a function to cells with different variables."""
        return self._map_region(func, "offdiag", kwargs)

    def map_diag(self, func: Callable[..., Any], **kwargs: Any) -> PairGrid:
        """Map a univariate function to cells with matching variables."""
        return self._map_region(func, "diag", kwargs)


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
) -> PairGrid:
    """Draw pairwise plots for numeric columns and distributions for matching columns."""
    grid = PairGrid(viewer, data, vars=vars, x_vars=x_vars, y_vars=y_vars, hue=hue, corner=corner)
    frame = grid._frame
    x_columns, y_columns = grid.x_vars, grid.y_vars
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
    diag_kws.pop("y", None)
    for options in (plot_kws, diag_kws):
        if (
            hue is not None
            and options.get("hue_order") is not None
            and options.get("hue_norm") is None
            and not isinstance(options.get("palette"), dict)
        ):
            options["palette"] = level_colors(options["hue_order"], options.get("palette"), options.get("color"))

    def plot_for(position: tuple[int, int]) -> tuple[Callable[..., Any], dict[str, Any]]:
        row, column = position
        x, y = x_columns[column], y_columns[row]
        if x == y:
            return diagonal, {**diag_kws, "x": x}
        return off_diagonal, {**plot_kws, "x": x, "y": y}

    grid._map(plot_for)
    return grid


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
    ratio: float = 5,
) -> JointGrid:
    """Draw a bivariate plot and its two marginal distributions."""
    joint = _select_kind(_BIVARIATE, kind)
    joint_kws = joint_kws or {}
    if hue is not None and kind == "reg":
        raise ValueError("jointplot does not support hue with kind='reg'.")
    if hue is not None:
        joint_kws = {**_hue_options(data, hue, joint_kws, continuous=kind == "scatter"), "hue": hue}
    marginal_kws = {**_hue_options(data, hue, marginal_kws or {}), "hue": hue}
    if isinstance(data, pd.DataFrame) and data.empty:
        return JointGrid(viewer, ratio=ratio)

    from napari_plot.components.viewer_model import ViewerModel

    margin = distributions.kdeplot if kind == "kde" else distributions.histplot
    prepared = []
    for panel, plot, options in (
        ("top", margin, {**marginal_kws, "x": x}),
        ("joint", joint, {**joint_kws, "x": x, "y": y}),
        ("right", margin, {**marginal_kws, "y": y}),
    ):
        stage = ViewerModel()
        plot(stage, data=data, **options)
        layers = list(stage.layers)
        for layer in layers:
            overlays = dict(layer._overlays)
            stage.layers.remove(layer)
            layer._overlays.update(overlays)
        prepared.append((panel, stage, layers))
    grid = JointGrid(viewer, ratio=ratio)
    legend_set = False
    for panel, stage, layers in prepared:
        for layer in layers:
            grid.add_layer(layer, panel=panel)
        if panel == "joint":
            grid.set_axis_labels(stage.axis.x_label, stage.axis.y_label)
            for field in ("x_scale", "y_scale", "x_categories", "y_categories"):
                setattr(viewer.axis, field, getattr(stage.axis, field))
        elif panel == "top":
            viewer.canvas.grid.joint_top_label = stage.axis.y_label
        elif panel == "right":
            viewer.canvas.grid.joint_right_label = stage.axis.x_label
        if stage.legend.entries and not legend_set:
            viewer.set_legend([entry.model_dump() for entry in stage.legend.entries])
            legend_set = True
    viewer.reset_view()
    return grid
