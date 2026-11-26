# Unreleased

## Improvements and fixes

- Canvas overlays (text, annotations, legend) sharing a position are now tiled inside the plot area instead of overlapping, following napari's `viewer.canvas.overlay_tiling`.
- Axis tick labels now follow their view when a layout change moves it without a resize (e.g. entering or leaving grid mode).
- Closed legend visuals no longer react to legend changes.
- In grid mode, zooming one axis (axis wheel, box zoom) no longer rescales the other axis when the canvas redraws.
- Double-clicking the x- or y-axis (of any plot cell in grid mode) resets that range again.
- Changing a layer's data no longer moves the cursor (and the crosshair) to the origin.
- The value-axis ticks of joint marginals no longer use the main plot's tick formatters.
- Streaming a `MultiLine` with lines of a different length now redraws their connections correctly.
- In grid mode, streaming data into a layer refits the bounds of the plot cell that draws it (e.g. an autoscaled joint marginal).
- Streaming data into a `MultiLine` or `Areas` layer refreshes its cached extent, so fits and resets use the new data.
- In grid mode, every plot cell has its own bottom layer for blending, so e.g. additive images in the main cell no longer wash out against a light background when a marginal layer is lower in the layer list.
- Autoscaled joint marginals keep their headroom above the largest value when all the data is in view.
- Dragging in an autoscaled joint marginal draws the zoom span across the marginal (a horizontal band in the right panel), whatever shape the active drag mode uses in the main panel.
- Image appearance changes (contrast limits, colormap, gamma, ...) and zoom-level (`scale_factor`) events no longer recompute the data extent of every layer.
- Updating the data or colors of `Bar` and `Areas` layers no longer recompiles their shader program.
- Plot cells no longer redraw their view when their axis direction is set to the value it already has.

## Added

- Added grid mode (`viewer.canvas.grid.enabled = True`): layers are shown side by side in plot cells with their own axes and a shared camera; gridded overlays (grid lines by default) are drawn in every cell.
  - A gridded legend (`viewer.legend.gridded = True`) lists only the layers of its cell.
- Right-dragging the x- or y-axis (of any plot cell in grid mode) pans the view along that axis only, and scrolling over it zooms that axis only, about the value under the mouse.
- Joint grids: `JointGrid(..., size=, autoscale=)` and `set_tick_formatter()`.
  - `size` (`grid.joint_size`) gives the marginals a fixed thickness in pixels; the main panel takes all the remaining space when the canvas is resized.
  - `autoscale` (`grid.joint_autoscale`) fits each marginal's value axis to the data visible in its shared range, and makes scrolling, dragging and double-clicking in a marginal act on its shared axis only.
  - Mouse events carry `event.joint_panel`, and `viewer.drag_tool.panel` holds the panel of the last press.
  - The crosshair draws only the shared line in each marginal.
- `Areas.stream()` replaces the areas quickly, keeping their colors and skipping the extent update.
- `Line`, `MultiLine` and `Areas` report their value range inside a range of either axis (`_get_region_extent`); `PlotGridCell` takes `x_tick_formatter`/`y_tick_formatter`.

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
