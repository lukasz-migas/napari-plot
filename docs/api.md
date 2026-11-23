# Public API

## Package exports

The following names are importable directly from `napari_plot`:

- `Viewer`: standalone Qt viewer.
- `ViewerModel`: viewer and layer state without constructing the main window.
- `NapariPlotWidget`: plot viewer for embedding in napari.
- `ScatterPlotWidget`: displayed-image-slice comparison widget for napari.
- `run()`: start the Qt event loop.
- `load_assets()`: initialize packaged icons and resources.
- `__version__`: installed package version.

## Viewer plotting methods

- `viewer.plot(y, **kwargs)` and `viewer.plot(x, y, **kwargs)` add a Line.
- `viewer.scatter(y, **kwargs)` and `viewer.scatter(x, y, **kwargs)` add Scatter points.
- `viewer.fill_between(x, y1, y2=0, **kwargs)` adds a Band.
- `viewer.errorbar(x, y, xerr=..., yerr=..., **kwargs)` adds an ErrorBar layer.
- `viewer.imshow(data, **kwargs)` adds one or more napari Image layers.
- `viewer.vbar(values, **kwargs)` and `viewer.vbar(x, height, **kwargs)` add vertical bars.
- `viewer.hbar(values, **kwargs)` and `viewer.hbar(y, length, **kwargs)` add horizontal bars.

- `viewer.fill_betweenx(y, x1, x2=0, **kwargs)` fills between x bounds.
- `viewer.axhline`, `axvline`, `axhspan`, and `axvspan` add reference marks.
- `viewer.text` and `annotate` label data, optionally with an annotation arrow.
- `viewer.stem`, `stackplot`, `hist`, and `rectangle` add Centroids,
  Areas, Bar, and Rectangles layers, respectively.

The `stats` extra provides statistical functions under `napari_plot.stats`
and on the viewer. Axes-level functions return a list of created layers.
`displot`, `catplot`, `lmplot`, `pairplot`, and `jointplot` return
a `FacetGrid` with access to each cell's layers.

Keyword arguments are forwarded to the corresponding layer constructor. The
lower-level methods `add_line`, `add_scatter`, `add_image`, `add_areas`, `add_band`, `add_bar`,
`add_error_bar`, `add_multi_line`, `add_centroids`, `add_text`, `add_rectangles`,
`add_region`, and `add_inf_line` are also public. `add_vectors` uses napari's
native Vectors interface.

## Layer classes

Layer classes are importable from `napari_plot.layers`:

```python
from napari_plot.layers import (
    Areas,
    Band,
    Bar,
    Centroids,
    ErrorBar,
    InfLine,
    Line,
    MultiLine,
    Rectangles,
    Region,
    Scatter,
    Text,
    Vectors,
)
```

Custom layers support the viewer layer list, visibility and opacity controls,
duplication, transforms, and VisPy visual registration. See the layer usage
examples for element selection and legend support.

## Models

`viewer.axis` controls axis visibility, labels, tick appearance, scale, category
labels, and runtime tick formatters. `viewer.legend` is a canvas overlay model
with visibility, position, entries, colors, marker and text sizes, spacing, and
border settings. Use `viewer.set_legend(...)` for explicit entries,
`viewer.set_legend_from_layers(...)` for plot-layer entries, or
`viewer.set_legend_from_points(...)` for categorized napari Points data.
`viewer.camera` and `viewer.drag_tool` expose navigation state.

`viewer.scene.camera` owns the custom plot camera. `viewer.camera` remains an
alias. The Canvas model exposes `viewer.canvas.size` in `(height, width)` order,
`background_color_override`, `overlay_tiling`, and `overlays`. Its `text`,
`legend`, and `grid_lines` overlays are the same instances exposed by the
existing viewer accessors. Native coordinate-grid and crosshair overlays are
not part of the plot scene.

Visible canvas overlays (text, `add_text_overlay(...)` annotations, legend) are
tiled inside the plot area like in napari: overlays sharing a position stack
instead of overlapping, in the order of `viewer.canvas.overlays`. The stacking
direction per position and the gap come from `viewer.canvas.overlay_tiling`
(e.g. `viewer.canvas.overlay_tiling.top_right = "vertical"`).

`viewer.canvas.grid` (a napari `GridCanvas` subclass) shows layers side by side: with
`enabled = True` each group of layers (`stride` layers, visible layers only)
gets its own plot cell with its own x/y axes, laid out in `shape` (`-1` picks
the size automatically) and separated by `spacing`. The `sharex` and `sharey`
options link the corresponding limits by default. Use `grid.cell(row, column)`
to set cell axis labels, scale, categories, or limits. Overlays with
`gridded = True` (the grid lines by default) are drawn and tiled in every cell;
the other overlays (text, annotations, legend) stay in the first cell. A
gridded legend lists only the layers of its cell; rows without a layer are
listed in every cell, and rows of layers shown in no cell in the first one.

The `viewer.canvas.grid.group_by_metadata` option defaults to `False`. Set it to
`True` to place layers sharing a string `napari_plot.group` metadata value in the
same cell. Visible ungrouped layers each get a cell, and the grid dimensions use the configured
shape or are calculated automatically. Assign a new dictionary to `layer.metadata` to emit the
metadata event and update the grid. When no visible layer has a group ID, the usual
stride and shape settings apply.

Layer `axis_labels` populate `viewer.dims.axis_labels` and the displayed plot
labels. Editing a plot label explicitly preserves that label across subsequent
metadata updates. Text layer `size` and legend `font_size` default to `None`,
which inherits the appearance font size. Explicit numeric sizes override it;
set the value back to `None` to resume inheritance. Axis fonts keep their
existing defaults.

Selecting multiple custom layers, or a mixture of custom and built-in layers,
provides shared opacity and blending controls. Custom single-layer panels stay
available even when napari's experimental dynamic-controls setting is enabled.

## Viewer reference

::: napari_plot.components.viewer_model.ViewerModel
    options:
      members:
        - xlim
        - ylim
        - reset_view
        - set_legend_from_layers
        - set_colorbar_from_layer
        - colorbar_for_cell
        - save_session
        - load_session
        - export_csv

## Layer reference

::: napari_plot.layers.centroids.centroids.Centroids
    options:
      members: false

::: napari_plot.layers.multiline.multiline.MultiLine
    options:
      members: false

::: napari_plot.layers.region.region.Region
    options:
      members: false

::: napari_plot.layers.infline.infline.InfLine
    options:
      members: false

::: napari_plot.layers.text.text.Text
    options:
      members: false
