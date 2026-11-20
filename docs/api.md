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
- `viewer.hbar(values, **kwargs)` and `viewer.hbar(y, width, **kwargs)` add horizontal bars.

- `viewer.boxplot`, `boxenplot`, `violinplot`, `barplot`, `stripplot`, `swarmplot`,
  `kdeplot`, `histplot`, `rugplot`, `distplot`, `heatmap`, `clustermap`, `scatterplot`,
  `lineplot` and `relplot` draw seaborn-style statistical plots. They mirror the
  functions in `napari_plot.stats` (same signatures without the viewer argument)
  and return the list of created layers.

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

Layer `axis_labels` populate `viewer.dims.axis_labels` and the displayed plot
labels. Editing a plot label explicitly preserves that label across subsequent
metadata updates. Text layer `size` and legend `font_size` default to `None`,
which inherits the appearance font size. Explicit numeric sizes override it;
set the value back to `None` to resume inheritance. Axis fonts keep their
existing defaults.

Selecting multiple custom layers, or a mixture of custom and built-in layers,
provides shared opacity and blending controls. Custom single-layer panels stay
available even when napari's experimental dynamic-controls setting is enabled.
