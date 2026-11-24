"""Generate screenshots and example pages from the runnable examples."""

from __future__ import annotations

import ast
import importlib.util
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from qtpy.QtGui import QImage
from qtpy.QtWidgets import QApplication

import napari_plot

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "assets" / "gallery"
DETAILS = ROOT / "docs" / "gallery"
GALLERY_PAGE = ROOT / "docs" / "gallery.md"
EXAMPLE_DIRS = (ROOT / "examples", ROOT / "examples_with_napari")
GITHUB_ROOT = "https://github.com/lukasz-migas/napari-plot/blob/main"


@dataclass(frozen=True)
class Example:
    """Metadata and source path for one gallery example."""

    path: Path
    title: str
    subtitle: str
    tags: tuple[str, ...]

    @property
    def slug(self) -> str:
        """Return a stable page name that includes the example collection."""
        collection = self.path.parent.name.removesuffix("_with_napari")
        return f"{collection}-{self.path.stem}"

    @property
    def source(self) -> str:
        """Return the repository-relative source path."""
        return self.path.relative_to(ROOT).as_posix()


def read_example(path: Path) -> Example:
    """Read title, subtitle, and tags from an example's module docstring."""
    source = path.read_text(encoding="utf-8")
    docstring = ast.get_docstring(ast.parse(source))
    if not docstring:
        raise ValueError(f"Example is missing its metadata docstring: {path}")

    lines = docstring.splitlines()
    if len(lines) < 3 or not lines[1].startswith("="):
        raise ValueError(f"Example docstring needs a title heading: {path}")
    title = lines[0].strip()
    body = "\n".join(lines[2:]).strip()
    tag_match = re.search(r"(?m)^\.\. tags::\s*(.+)$", body)
    if not tag_match:
        raise ValueError(f"Example docstring needs a '.. tags::' line: {path}")
    tags = tuple(tag.strip() for tag in tag_match.group(1).split(",") if tag.strip())
    subtitle = body[: tag_match.start()].strip().split("\n\n", maxsplit=1)[0].replace("\n", " ")
    if not subtitle:
        raise ValueError(f"Example docstring needs a subtitle: {path}")
    return Example(path=path, title=title, subtitle=subtitle, tags=tags)


def discover_examples() -> list[Example]:
    """Find every Python example and read its required gallery metadata."""
    return [read_example(path) for directory in EXAMPLE_DIRS for path in sorted(directory.glob("*.py"))]


def load_example(example: Example) -> tuple[object, object]:
    """Import an example and return its module and viewer instance."""
    module_name = f"_napari_plot_docs_{example.slug.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, example.path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load example at {example.path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    viewers = [value for value in vars(module).values() if isinstance(value, napari_plot.Viewer)]
    if len(viewers) == 1:
        return module, viewers[0]

    napari_viewers = [value for value in vars(module).values() if value.__class__.__module__.startswith("napari.") and value.__class__.__name__ == "Viewer"]
    if len(napari_viewers) == 1:
        return module, napari_viewers[0]
    raise RuntimeError(f"Expected one napari-plot or napari Viewer in {example.path}, found {len(viewers) + len(napari_viewers)}")


def render_example(example: Example, app: QApplication) -> Path:
    """Import one example and save a full-window screenshot as a PNG."""
    np.random.seed(0)
    module, viewer = load_example(example)
    image_path = OUTPUT / f"{example.slug}.png"
    if isinstance(viewer, napari_plot.Viewer):
        viewer.window.resize(1400, 720)
        viewer.reset_view()
        app.processEvents()
        viewer.export_figure(image_path, dpi=144)
    else:
        window = viewer.window._qt_window
        window.resize(1400, 900)
        window.show()
        app.processEvents()
        window.grab().save(str(image_path))
    viewer.close()
    del module
    return image_path


def write_detail(example: Example, image_name: str) -> None:
    """Write a detail page with description, screenshot, source, and code."""
    source = example.path.read_text(encoding="utf-8").rstrip()
    tags = ", ".join(f"`{tag}`" for tag in example.tags)
    github_url = f"{GITHUB_ROOT}/{example.source}"
    page = (
        f"# {example.title}\n\n{example.subtitle}\n\n"
        f"**Tags:** {tags}\n\n"
        f"![{example.title} example screenshot](../assets/gallery/{image_name})\n\n"
        f"[View the source file on GitHub]({github_url})\n\n"
        "## Python example\n\n"
        f"```python\n{source}\n```\n"
    )
    (DETAILS / f"{example.slug}.md").write_text(page, encoding="utf-8")


def write_gallery_pages(examples: list[Example]) -> None:
    """Write a detail page and gallery card for every discovered example."""
    cards = []
    for example in examples:
        image_name = f"{example.slug}.jpg"
        write_detail(example, image_name)
        tag_chips = " ".join(f'<span class="gallery-tag">{tag}</span>' for tag in example.tags)
        cards.append(
            f'<a class="gallery-card" href="gallery/{example.slug}.md">'
            f'<img src="assets/gallery/{image_name}" alt="{example.title} example screenshot">'
            f'<span class="gallery-card-copy"><strong>{example.title}</strong>'
            f"<span>{example.subtitle}</span><span class=\"gallery-tags\">{tag_chips}</span></span></a>"
        )

    GALLERY_PAGE.write_text(
        "# Example gallery\n\n"
        "Select a tile to see its description, screenshot, Python code, and GitHub source.\n\n"
        '<div class="gallery-grid">\n\n' + "\n\n".join(cards) + "\n\n</div>\n",
        encoding="utf-8",
    )


def render_gallery() -> None:
    """Render all examples, optimize screenshots, and generate the gallery."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    DETAILS.mkdir(parents=True, exist_ok=True)
    for pattern in ("*.png", "*.jpg", "*.jpeg"):
        for old_image in OUTPUT.glob(pattern):
            old_image.unlink()
    for old_page in DETAILS.glob("*.md"):
        old_page.unlink()

    app = QApplication.instance() or QApplication([])
    examples = discover_examples()
    image_paths = [render_example(example, app) for example in examples]
    subprocess.run(["bash", str(ROOT / "tools" / "optimize-images.sh"), *map(str, image_paths)], check=True, cwd=ROOT)
    # The optimizer may skip PNGs when JPEG conversion would increase their size.
    # Gallery output still uses one predictable format, so convert those leftovers.
    for png_path in OUTPUT.glob("*.png"):
        jpg_path = png_path.with_suffix(".jpg")
        if not QImage(str(png_path)).save(str(jpg_path), "JPEG", 90):
            raise RuntimeError(f"Could not convert screenshot to JPEG: {png_path}")
        png_path.unlink()

    write_gallery_pages(examples)


if __name__ == "__main__":
    render_gallery()
