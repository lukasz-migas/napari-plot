# Unreleased

## Improvements and fixes

- Canvas overlays (text, annotations, legend) sharing a position are now tiled inside the plot area instead of overlapping, following napari's `viewer.canvas.overlay_tiling`.
- Axis tick labels now follow their view when a layout change moves it without a resize (e.g. entering or leaving grid mode).
- Closed legend visuals no longer react to legend changes.
- In grid mode, zooming one axis (axis wheel, box zoom) no longer rescales the other axis when the canvas redraws.
- Double-clicking the x- or y-axis (of any plot cell in grid mode) resets that range again.

## Added

- Added grid mode (`viewer.canvas.grid.enabled = True`): layers are shown side by side in plot cells with their own axes and a shared camera; gridded overlays (grid lines by default) are drawn in every cell.
  - A gridded legend (`viewer.legend.gridded = True`) lists only the layers of its cell.
- Right-dragging the x- or y-axis (of any plot cell in grid mode) pans the view along that axis only, and scrolling over it zooms that axis only, about the value under the mouse.

# napari-plot v0.3.1

Changes since `v0.2.0`.

## Added

- Added `Bar` layers with vertical and horizontal orientations.
  - Supports positions, values, baseline, bar width, fill and border colors, border width, opacity, selection, and removal of selected bars.
  - Added bar-layer controls and `vbar()` / `hbar()` convenience methods.
- Added `Text` layers with per-label text and colors, font styling, alignment, rotation, and offsets.
- Added interactive plot legends with automatic layer entries, custom entries, `Points`-property legends, synchronization, placement, and styling controls.
- Added logarithmic axes with positive-value validation and log tick generation.
- Added categorical axes with configurable ordered category labels.
- Added axis controls for linear, logarithmic, and categorical scales.
- Added the concise plotting API: `plot()`, `scatter()`, `imshow()`, `vbar()`, and `hbar()`.
- Added lazy imports for the top-level package.
- Added a complete Add Layer menu for supported napari-plot and napari layer types.
- Added extensive examples and API/usage documentation.

## Improvements and fixes

- Migrated to napari `0.8.0` and updated associated APIs, event handling, and Pydantic validation.
- Improved axis tick formatting, label-overlap handling, and custom tick formatter support.
- Improved region and infinite-line rendering using batched VisPy visuals.
- Improved region and infinite-line selection, opacity, visibility, extent calculation, and rendering updates.
- Improved camera drag and mouse-release handling.
- Improved layer duplication, registration, context menus, and layer controls.
- Improved embedded napari widgets with host-theme synchronization.
- Updated the scatter widget to use the currently displayed slices of selected image layers, support nD images, and report mismatched slice shapes clearly.
- Added broader test coverage for axes, legends, bars, text, rendering, controls, duplication, registration, and plotting helpers.

## Compatibility and packaging

- Python `3.11+` is now required.
- napari `0.8.0` is required.
- Qt6 is now the default configuration through PyQt6 or PySide6.
- Replaced the legacy tox-oriented development setup with uv dependency groups and workflows.
- Updated CI workflows, GitHub Actions versions, pre-commit configuration, and release/deployment automation.
- Renamed the top-level public model export from `ViewerModel1D` to `ViewerModel`.
- Updated CI and deployment workflow configuration.
