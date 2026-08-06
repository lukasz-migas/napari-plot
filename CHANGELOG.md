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
