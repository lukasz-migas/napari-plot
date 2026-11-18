"""Normalize seaborn-style inputs (long-form frames, wide-form tables, plain arrays)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd

Orient = Literal["v", "h"]

_ORIENT_ALIASES = {"v": "v", "x": "v", "vertical": "v", "h": "h", "y": "h", "horizontal": "h"}


def parse_orient(orient: str | None) -> Orient | None:
    """Return ``"v"``/``"h"`` from seaborn-style orientation aliases."""
    if orient is None:
        return None
    try:
        return _ORIENT_ALIASES[str(orient).lower()]  # type: ignore[return-value]
    except KeyError:
        raise ValueError(f"orient must be one of {sorted(_ORIENT_ALIASES)}, not {orient!r}.") from None


def _as_frame(data: Any) -> pd.DataFrame | None:
    """Convert dict-like data to a DataFrame for column lookups."""
    if data is None or isinstance(data, pd.DataFrame):
        return data
    if isinstance(data, Mapping):
        return pd.DataFrame({key: pd.Series(np.asarray(value)) for key, value in data.items()})
    return None


def _resolve(frame: pd.DataFrame | None, var: Any) -> tuple[pd.Series | None, str | None]:
    """Return a variable as a Series together with its display label."""
    if var is None:
        return None, None
    if isinstance(var, str):
        if frame is None or var not in frame.columns:
            raise ValueError(f"Could not interpret value {var!r}: no such column in data.")
        return frame[var].reset_index(drop=True), var
    if isinstance(var, pd.Series):
        return var.reset_index(drop=True), None if var.name is None else str(var.name)
    values = np.asarray(var)
    if values.ndim != 1:
        raise ValueError("Plot variables must be one-dimensional.")
    return pd.Series(values), None


def long_frame(data: Any = None, *, dropna: tuple[str, ...] = (), **variables: Any) -> tuple[pd.DataFrame, dict]:
    """Collect named plot variables into one DataFrame.

    Parameters
    ----------
    data : DataFrame, dict or None
        Source for variables given as column names.
    dropna : tuple of str
        Variables whose missing values drop the whole row.
    **variables
        Mapping of semantic name (``x``, ``y``, ``hue``, ...) to a column name, Series or array.

    Returns
    -------
    frame : DataFrame
        One column per supplied variable, named after its semantic role.
    labels : dict
        Display label per semantic role (column name or Series name, else None).
    """
    frame = _as_frame(data)
    columns, labels = {}, {}
    for role, var in variables.items():
        series, label = _resolve(frame, var)
        if series is not None:
            columns[role] = series
            labels[role] = label
    lengths = {len(series) for series in columns.values()}
    if len(lengths) > 1:
        raise ValueError("All plot variables must have the same length.")
    result = pd.DataFrame(columns)
    present = [role for role in dropna if role in result.columns]
    if present:
        result = result.dropna(subset=present).reset_index(drop=True)
    return result, labels


@dataclass
class CategoricalData:
    """Values grouped by category (and optionally hue level) for categorical plots."""

    categories: list[Any]
    labels: list[str]
    hue_levels: list[Any] | None
    groups: dict[tuple[Any, Any], np.ndarray]
    orient: Orient
    category_label: str | None = None
    value_label: str | None = None
    hue_label: str | None = None
    color_by_category: bool = False

    def values(self, category: Any, hue: Any = None) -> np.ndarray:
        """Return the values of one category/hue cell (empty when missing)."""
        return self.groups.get((category, hue), np.empty(0))

    @property
    def all_values(self) -> np.ndarray:
        """All plotted values concatenated."""
        arrays = [values for values in self.groups.values() if len(values)]
        return np.concatenate(arrays) if arrays else np.empty(0)


def _wide_frame(data: Any) -> tuple[pd.DataFrame, str | None]:
    """Melt wide-form data into ``cat``/``val`` columns."""
    if isinstance(data, pd.DataFrame):
        numeric = data.select_dtypes("number")
        frame = numeric.melt(var_name="cat", value_name="val")
        label = None if data.columns.name is None else str(data.columns.name)
        return frame, label
    if isinstance(data, Mapping):
        pieces = [pd.DataFrame({"cat": key, "val": np.asarray(values, dtype=float)}) for key, values in data.items()]
        return pd.concat(pieces, ignore_index=True), None
    if isinstance(data, np.ndarray) and data.ndim == 2:
        return pd.DataFrame(data).melt(var_name="cat", value_name="val"), None
    if isinstance(data, (list, tuple)) and data and np.ndim(data[0]) == 1:
        pieces = [pd.DataFrame({"cat": i, "val": np.asarray(v, dtype=float)}) for i, v in enumerate(data)]
        return pd.concat(pieces, ignore_index=True), None
    values = np.asarray(data, dtype=float)
    if values.ndim != 1:
        raise ValueError("Could not interpret data for a categorical plot.")
    return pd.DataFrame({"cat": "", "val": values}), None


def _infer_orient(frame: pd.DataFrame, orient: Orient | None) -> Orient:
    """Choose the categorical axis like seaborn does."""
    if orient is not None:
        return orient
    has_x, has_y = "x" in frame.columns, "y" in frame.columns
    if has_x and not has_y:
        return "h"
    if has_y and not has_x:
        return "v"
    x_numeric = pd.api.types.is_numeric_dtype(frame["x"])
    y_numeric = pd.api.types.is_numeric_dtype(frame["y"])
    return "h" if x_numeric and not y_numeric else "v"


def normalize_categorical(
    data: Any = None,
    *,
    x: Any = None,
    y: Any = None,
    hue: Any = None,
    order: list | None = None,
    hue_order: list | None = None,
    orient: str | None = None,
) -> CategoricalData:
    """Group values by category and hue level for categorical plots.

    Long-form input names ``x``/``y``/``hue`` columns of ``data`` (or passes vectors). Without ``x`` and ``y``,
    ``data`` is wide-form: DataFrame columns, dict keys, 2D-array columns or list items become categories.
    """
    from napari_plot.stats._seaborn import categorical_order

    parsed = parse_orient(orient)
    labels: dict = {}
    if x is None and y is None:
        frame, category_label = _wide_frame(data)
        resolved: Orient = parsed or "v"
        value_label = None
    else:
        frame, labels = long_frame(data, x=x, y=y, hue=hue)
        resolved = _infer_orient(frame, parsed)
        cat_role, val_role = ("x", "y") if resolved == "v" else ("y", "x")
        if val_role not in frame.columns:
            raise ValueError("Categorical plots need a numeric value variable.")
        cat = frame[cat_role] if cat_role in frame.columns else pd.Series([""] * len(frame))
        frame = pd.DataFrame({"cat": cat, "val": frame[val_role], **({"hue": frame["hue"]} if "hue" in frame else {})})
        category_label, value_label = labels.get(cat_role), labels.get(val_role)

    frame = frame.dropna(subset=["val"])
    frame["val"] = frame["val"].astype(float)
    categories = list(categorical_order(frame["cat"], order))
    color_by_category = False
    hue_levels = None
    if "hue" in frame.columns:
        # seaborn idiom ``hue=x``: color each category instead of dodging hue levels
        if frame["hue"].astype(str).equals(frame["cat"].astype(str)):
            color_by_category = True
            frame = frame.drop(columns="hue")
        else:
            hue_levels = list(categorical_order(frame["hue"], hue_order))

    groups: dict[tuple[Any, Any], np.ndarray] = {}
    for category in categories:
        in_category = frame["cat"] == category
        for level in hue_levels or [None]:
            mask = in_category if level is None else in_category & (frame["hue"] == level)
            values = frame.loc[mask, "val"].to_numpy()
            if len(values):
                groups[(category, level)] = values

    return CategoricalData(
        categories=categories,
        labels=[str(category) for category in categories],
        hue_levels=hue_levels,
        groups=groups,
        orient=resolved,
        category_label=category_label,
        value_label=value_label,
        hue_label=labels.get("hue"),
        color_by_category=color_by_category,
    )
