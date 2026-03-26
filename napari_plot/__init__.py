"""Init"""

from __future__ import annotations

import importlib
import typing as ty

try:
    from napari_plot._version import version as __version__
except ImportError:
    __version__ = "unknown"
    from napari_plot.resources import load_assets

    load_assets()


__all__ = (
    "NapariPlotWidget",
    "ScatterPlotWidget",
    "Viewer",
    "ViewerModel",
    "__version__",
    "load_assets",
    "run",
)


# Map exported names -> (module, attribute)
_LAZY_IMPORTS = {
    "NapariPlotWidget": ("napari_plot._plot_widget", "NapariPlotWidget"),
    "run": ("napari_plot._qt.qt_event_loop", "run"),
    "ScatterPlotWidget": ("napari_plot._scatter_widget", "ScatterPlotWidget"),
    "ViewerModel": ("napari_plot.components.viewer_model", "ViewerModel"),
    "Viewer": ("napari_plot.viewer", "Viewer"),
}


def __getattr__(name: str) -> ty.Any:
    """Lazily import objects when accessed."""
    # Need to import to ensure that `napari_plot` is included in the auto-class generator
    from napari_plot.utils import _register  # isort:skip noqa

    del _register
    try:
        module_name, attr_name = _LAZY_IMPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None

    module = importlib.import_module(module_name)
    value = getattr(module, attr_name)

    # Cache so future access is fast
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals().keys()) | set(__all__))
