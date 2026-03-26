# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

napari-plot is a napari plugin providing 1D plotting support. It can be used as an embedded dock widget within napari or as a standalone plotting application. It supports PyQt5, PyQt6, PySide2, and PySide6 backends via `qtpy`.

## Commands

### Install
```bash
pip install -e '.[all]'       # All extras
pip install -e '.[testing]'   # Testing deps only
```

### Testing
```bash
pytest                                            # Run all tests
pytest tests/layers/scatter/test_scatter.py       # Run single file
pytest tests/layers/scatter/test_scatter.py::test_name  # Run single test
pytest --cov=napari_plot                          # With coverage
```

### Linting & Formatting
```bash
ruff check .        # Lint
ruff format .       # Format (double quotes, 120-char lines)
pre-commit run -a   # Run all hooks (absolufy-imports, isort, ruff, import-linter)
```

### Multi-environment testing
```bash
tox -e py311-linux-pyqt6   # Specific environment
```

## Architecture

The codebase follows napari's layered architecture pattern with a clean separation between data models, rendering, and UI.

### Layer: Data Model (`components/`)
Core state lives here. `ViewerModel` (in `viewer_model.py`) is the central model containing `LayerList`, `Axis`, `Camera`, `DragTool`, and other state. It follows napari's evented model pattern — properties emit events that drive UI updates reactively.

### Layer: Plot Layers (`layers/`)
Each plot type is its own layer class (Line, Scatter, Region, InfLine, Centroids, MultiLine). Each layer has a `_type_string` and follows napari's layer protocol. Layers hold data and emit events when data changes.

### Layer: Vispy Rendering (`_vispy/`)
Translates layer/component model events into Vispy scene graph updates. `VispyCanvas` is the main rendering surface. Each layer type has a corresponding Vispy layer class under `_vispy/layers/`. Tools and overlays (axes, grid, labels) also live here.

### Layer: Qt UI (`_qt/`)
Qt widgets for the viewer window, layer list, layer controls, and toolbars. Layer controls (in `_qt/layer_controls/`) provide property editing UIs per layer type. The main window is in `_qt/qt_main_window.py`.

### Layer: App Model (`_app_model/`)
Declarative command/menu/keybinding definitions using `app-model`. Actions are registered here and tied to the viewer via context injection.

### Plugin Entry Points
`napari.yaml` defines two widgets registered with napari: `NapariPlotWidget` (embedded 1D plot) and `ScatterPlotWidget` (2D scatter).

## Key Patterns

- **Evented models**: All model classes use `napari.utils.events.EventedModel` or similar. UI listens to model events rather than polling.
- **Lazy imports**: `napari_plot/__init__.py` uses lazy loading to keep import time fast. When adding new public exports, follow the existing lazy import pattern.
- **Qt backend agnosticism**: Always import Qt via `qtpy` (e.g. `from qtpy.QtWidgets import ...`), never directly from PyQt5/6 or PySide2/6.
- **Layer protocol**: New layer types must implement the standard layer interface. See existing layers for the required methods (`_get_state`, `_set_view_slice`, etc.).

## Code Style

- Line length: 120 characters
- Quotes: double quotes
- Import style: absolute imports (enforced by absolufy-imports pre-commit hook)
- Type annotations expected (mypy strict mode configured)
