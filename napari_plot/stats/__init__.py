"""Seaborn-style statistical plots built from napari-plot layers."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_PLOT_MODULES = {
    "categorical": ("barplot", "boxenplot", "boxplot", "countplot", "pointplot", "stripplot", "swarmplot", "violinplot"),
    "distributions": ("distplot", "ecdfplot", "histplot", "kdeplot", "rugplot"),
    "facets": ("catplot", "displot", "jointplot", "lmplot", "pairplot"),
    "matrix": ("clustermap", "heatmap"),
    "relational": ("lineplot", "regplot", "relplot", "scatterplot"),
}

_PLOTS = {name: module for module, names in _PLOT_MODULES.items() for name in names}
__all__ = sorted(_PLOTS)


def __getattr__(name: str) -> Any:
    """Load a statistical plotting function on first access."""
    module = "facets" if name in {"FacetGrid", "PairGrid"} else _PLOTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    try:
        value = getattr(import_module(f"{__name__}.{module}"), name)
    except ModuleNotFoundError as error:
        if error.name in {"pandas", "scipy", "seaborn", "matplotlib"}:
            raise ImportError("Install napari-plot[stats] to use statistical plotting.") from error
        raise
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """List statistical plotting functions alongside loaded members."""
    return sorted(set(globals()) | set(__all__) | {"FacetGrid", "PairGrid"})
