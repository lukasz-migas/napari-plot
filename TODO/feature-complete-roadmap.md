# napari-plot: remaining items to reach feature-complete

## Status

Items 1-4, 7, 8, 10-20 of the original audit are implemented and
removed from this list (item 16 without view history, which was dropped). The full suite has 837 passing tests on
macOS with native Qt and OpenGL. Remaining items keep their original numbers.

Outside the list (do now): `codecov.yml:10` has a plaintext Codecov token - rotate it and move it to a CI secret.

## P1 - core plotting gaps
5. **Line styling**: dash styles, markers-on-line, step (`drawstyle`) for Line/MultiLine/Centroids (only InfLine has dashes). Legend swatches should reflect style. Also unblocks `lineplot` style/size/dashes in stats.
6. **Per-vertex color / colormap on Line and MultiLine** (`line.py:100` is a single RGBA).
9. **Twin / secondary y-axis** (independent y range per layer group).

## Follow-ups
- **ionglow hover readout**: switch ionglow's `LineHoverReadout` to napari-plot's `viewer.hover` / `viewer.crosshair` (item 16), keeping its m/z and mobility formatting through `viewer.hover.formatter`.

## Verification (per item, when implemented)
- `uv run pytest tests/` plus new targeted tests per item (pytest-qt for Qt items).
- Manual: run `examples/*.py` relevant to the change and embedded mode via `examples_with_napari/`.

