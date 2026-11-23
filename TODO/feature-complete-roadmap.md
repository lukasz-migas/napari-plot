# napari-plot: top 20 items to reach feature-complete

## Implementation status

- P0 items 2, 3, and 4 are implemented. The selection event adds per-layer
  indices while preserving the existing drag vertices and coordinate convention.
- P1 items 7, 8, 10, 11, 12, 13, and 14 are implemented. Colorbars reuse
  napari's visual with right and bottom placement and independent cell settings.
- P2 items 15, 18, 19, and 20 are implemented. Vector export embeds image
  layers as bitmaps, session files can restore plotted data and settings,
  and custom Python formatters can be reapplied after loading. Mypy in CI
  starts with the axis, colorbar, line, and band models and data I/O.

Verification passed on macOS with native Qt and OpenGL. The full suite contains
746 passing tests. Live figure and ROI exports, the strict documentation build,
and the wheel and source distribution checks also passed.

The entries below preserve the original audit.

## Context
Review of the whole library (layers, viewer/axes, Qt, napari integration, stats, tests/docs/packaging) to list what is missing, half-done or broken. Ordered by priority: P0 = broken or harmful, P1 = core plotting gaps, P2 = polish/ecosystem. Key claims were spot-checked in source.

Outside the list (do now): `codecov.yml:10` has a plaintext Codecov token - rotate it and move it to a CI secret.

## P0 - broken or harmful
1. **Stop wiping host napari shortcuts.** `_qt/qt_viewer.py:45` calls `reset_default_keymap()` at import, which clears `default_shortcuts` and `settings.shortcuts` (`_qt/_qapp_model/__init__.py:54`). Embedding the widget breaks napari keybindings and may persist. Scope the keymap to the plot viewer.
2. **Fix export paths.** `Window.clipboard` passes `flash` as `size` (`qt_main_window.py:1487` vs `_screenshot` sig `:1236`); `export_figure` calls `reset_view(margin=0)` but `reset_view` has no `margin` (`viewer_model.py:828`); `export_rois` uses `camera.center` (absent); `fit_to_data_extent` uses image `extent.step`. Add tests for each menu export.
3. **Selection tools that return data.** Lasso/polygon/box only set `drag_tool.vertices` (`_viewer_mouse_bindings.py:51,87,110`); nothing hit-tests layers. Add `selected_data` on Scatter/Line/MultiLine/Bar/Centroids + a `viewer.events.selection` with indices per layer.
4. **Theme-aware axes and legend.** Axis tick/label colors default to white (`components/axis.py:72`), legend defaults dark (`components/legend.py:33`); light napari theme gives white-on-white. Derive from `viewer.theme`.

## P1 - core plotting gaps
5. **Line styling**: dash styles, markers-on-line, step (`drawstyle`) for Line/MultiLine/Centroids (only InfLine has dashes). Legend swatches should reflect style.
6. **Per-vertex color / colormap on Line and MultiLine** (`line.py:100` is a single RGBA).
7. **Axis model completion**: inverted axes (blocked by `_check_range` reorder, `_vispy/components/camera.py:209`), toggleable minor ticks + minor grid, scientific/offset notation, datetime axis, fix "power" scale (`return NotImplementedError`, `_vispy/components/axis.py:350`), resetting a tick formatter to `None`.
8. **Unified limits API**: `viewer.xlim/ylim` get/set, `autoscale` toggle, data margins; consolidate `set_x_view`/`set_x_range`/`camera.rect`.
9. **Twin / secondary y-axis** (independent y range per layer group).
10. **Grid mode sharex/sharey + per-cell axes** (labels, scale, range per cell; today one camera + one Axis for all cells, `_vispy/plot_cell.py:93`).
11. **Missing convenience wrappers + consistent signatures**: `axhline/axvline`, `axhspan/axvspan`, `text/annotate` (with arrows), `stem`, `stackplot`, `hist`, `fill_betweenx`, `rectangle`; fix `hbar(width=)` clash and `bottom/left` -> `baseline`; harmonise `color/width/face_color/fill_color` naming and Scatter `(y, x)` order.
12. **Interactive editing parity**: Scatter add/select/delete (modes disabled, `scatter.py:122`), Bar delete from GUI, Rectangles add/move/resize, Text drag. Plus Qt control gaps: Areas fill/border/orientation, InfLine `line_style`, Centroids orientation; fix Region controls double `delete_button` (`qt_region_controls.py:66,120`).
13. **Colorbar completion**: works for Scatter `face_colormap` (currently only `colormap`, `viewer_model.py:629`), orientation/position, log norm, per-cell, Qt controls.
14. **Legend completion**: Rectangles entry (`components/legend.py:228`), `ncols`, title, outside-plot placement.

## P2 - workflow, ecosystem, quality
15. **Vector + data export and sessions**: SVG/PDF, DPI option, per-layer CSV export, save/load session (`json()` excludes layers, `viewer_model.py:75`); restore drag-and-drop open (`qt_viewer.py:586` commented out).
16. **Interaction QoL**: view history (back/forward), crosshair + coordinate readout, hover tooltips with real data values (`Line/Centroids._get_value` return cursor, `line.py:203`), shortcuts for tools/reset/export, canvas context menu; replace image-oriented layer-list context actions (`_layerlist_context_actions.py:78-244`).
17. **napari integrations**: line profile from a Shapes line, image histogram linked to contrast limits, z/t-profile under cursor, plot from layer `features`, link plot selection back to Points/Labels; add npe2 menu contributions + sample data; drop dead npe1 `_contribution.py`.
18. **Stats completeness**: ecdfplot, countplot, pointplot, regplot/lmplot, displot/catplot, pairplot/jointplot + FacetGrid (needs #10); bivariate hist/kde, `histplot(element=, fill=)`, `kdeplot(multiple=)`, `lineplot` style/size/dashes (needs #5), `scatterplot(group=)`.
19. **Tests**: visual-regression (image comparison) for layers/overlays, key-binding tests, untested vispy layers (areas, band, error_bar, centroids, multiline), centroids controls, overlays (colorbar, text), benchmarks for large data.
20. **Docs + packaging cleanup**: enable mkdocstrings API pages and an examples gallery; document Centroids/MultiLine/Region/InfLine/Text/selection/colorbar; refresh README roadmap; fix `.readthedocs.yaml` (Python 3.9); move pandas/scipy/seaborn/matplotlib to a `stats` extra; relax `napari==0.10.0`; drop `napari-plugin-engine`; remove stale `misc/setup.cfg`, `Makefile`, `requirements.txt`, duplicate dependabot/renovate; delete dead code (`components/gridlines.py`, `_vispy/utils/axis.py:tick_formatter`, 3D/`ndisplay` remnants); add `py.typed` + mypy in CI; raise annotations in line/scatter/infline/region/centroids and `_qt` (~58% overall).

## Verification (per item, when implemented)
- `uv run pytest tests/` plus new targeted tests per item (pytest-qt for Qt items).
- Manual: run `examples/*.py` relevant to the change and embedded mode via `examples_with_napari/`; for #1 confirm napari shortcuts survive opening the widget.
