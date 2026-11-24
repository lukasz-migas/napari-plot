"""Generate screenshots and the documentation gallery from runnable examples."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from qtpy.QtWidgets import QApplication

import napari_plot

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "assets" / "gallery"
GALLERY_PAGE = ROOT / "docs" / "gallery.md"
EXAMPLES = (
    ("add_simple_lines", "Line plots", "Two line series with labeled axes."),
    ("add_scatter_with_text", "Scatter and labels", "Color points from data features and attach labels."),
    ("add_bars_and_legend", "Bars and legend", "Compare vertical and horizontal bars with a linked legend."),
    ("add_band", "Bands", "Show an interval around a measured profile."),
    ("add_error_bars", "Error bars", "Display asymmetric measurement intervals."),
    ("add_plot_annotations", "Annotations", "Mark a baseline, integration window, and peak."),
    ("add_rectangles", "Rectangles", "Mark regions of interest with rectangle layers."),
    ("add_categorical_axes", "Categorical axes", "Use named categories on both plot axes."),
    ("show_grid_mode", "Small multiples", "Compare several signals in synchronized plot cells."),
    ("stats_boxplot", "Grouped box plots", "Compare distributions by day and smoking status."),
    ("stats_distributions", "Distributions", "Compare stacked histograms with density curves."),
    ("stats_heatmap", "Heatmap", "Read values from an annotated image layer."),
)


def load_example(name: str) -> tuple[object, napari_plot.Viewer]:
    """Import one example module and return it with its viewer."""
    path = ROOT / "examples" / f"{name}.py"
    module_name = f"_napari_plot_docs_{name}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load example at {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    viewers = [value for value in vars(module).values() if isinstance(value, napari_plot.Viewer)]
    if len(viewers) != 1:
        raise RuntimeError(f"Expected one Viewer in {path}, found {len(viewers)}")
    return module, viewers[0]


def render_gallery() -> None:
    """Render selected examples and write their linked gallery page."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for old_image in OUTPUT.glob("*.png"):
        old_image.unlink()
    app = QApplication.instance() or QApplication([])

    cards = []
    for name, title, description in EXAMPLES:
        module, viewer = load_example(name)
        image_name = f"{name}.png"
        image_path = OUTPUT / image_name
        viewer.window.resize(1400, 720)
        viewer.reset_view()
        app.processEvents()
        viewer.export_figure(image_path, dpi=144)
        viewer.close()
        del module

        source = f"https://github.com/lukasz-migas/napari-plot/blob/main/examples/{name}.py"
        cards.append(
            f'<a class="gallery-card" href="{source}">'
            f'<img src="assets/gallery/{image_name}" alt="{title} example screenshot">'
            f'<span class="gallery-card-copy"><strong>{title}</strong>'
            f"<span>{description}</span></span></a>"
        )

    GALLERY_PAGE.write_text(
        "# Example gallery\n\n"
        "Each tile shows a figure rendered from its runnable Python example. "
        "Select a tile to open the source code on GitHub.\n\n"
        '<div class="gallery-grid">\n\n'
        + "\n\n".join(cards)
        + "\n\n</div>\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    render_gallery()
