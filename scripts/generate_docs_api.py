"""Generate API reference directives from the package's public exports."""

from __future__ import annotations

import importlib
from pathlib import Path

from napari_plot import layers, stats

ROOT = Path(__file__).resolve().parents[1]
API_PAGE = ROOT / "docs" / "api.md"


def module_directive(module: str, members: list[str]) -> str:
    """Return a mkdocstrings directive for a module's public exports."""
    member_lines = "\n".join(f"        - {member}" for member in members)
    return f"::: {module}\n    options:\n      members:\n{member_lines}\n"


def stats_directives() -> str:
    """Return API directives for every function exported by the stats package."""
    directives = []
    for name in stats.__all__:
        function = getattr(stats, name)
        source_module = importlib.import_module(function.__module__)
        directives.append(f"::: {source_module.__name__}.{name}\n")
    return "\n".join(directives)


def generate_api_page() -> None:
    """Write API directives from public classes and module export lists."""
    parts = [
        "# API reference\n\n"
        "Class signatures, methods, and docstrings are rendered from the Python source. "
        "The layer and stats sections follow their modules' `__all__` exports, so new public "
        "classes and plotting functions appear here on the next docs build.\n",
        "## Viewer and layout classes\n",
        '::: napari_plot.viewer.Viewer\n    options:\n      members: true\n      inherited_members: false\n      filters: ["!^_"]\n',
        '::: napari_plot.components.viewer_model.ViewerModel\n    options:\n      members: true\n      filters: ["!^_"]\n',
        '::: napari_plot.components.joint_grid.JointGrid\n    options:\n      members: true\n      filters: ["!^_"]\n',
        "## napari widgets\n",
        '::: napari_plot._plot_widget.NapariPlotWidget\n    options:\n      members: true\n      inherited_members: false\n      filters: ["!^_"]\n',
        '::: napari_plot._scatter_widget.ScatterPlotWidget\n    options:\n      members: true\n      inherited_members: false\n      filters: ["!^_"]\n',
        "## Plot layers\n",
        module_directive("napari_plot.layers", layers.__all__),
        "## Statistical plots\n",
        stats_directives(),
    ]
    API_PAGE.write_text("\n".join(parts), encoding="utf-8")


if __name__ == "__main__":
    generate_api_page()
