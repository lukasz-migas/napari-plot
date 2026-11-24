# Advanced workflows

## Standalone viewer

Create a `Viewer`, add layers, and start the Qt event loop:

```python
import numpy as np
import napari_plot

viewer = napari_plot.Viewer(title="Measurements")
x = np.linspace(0.1, 10, 200)
viewer.plot(x, np.sin(x), name="line", color="cyan")
viewer.scatter(x[::10], np.sin(x[::10]), name="samples", size=8)
napari_plot.run()
```

The concise plotting methods accept conventional x and y arguments. `plot(y)`
and `scatter(y)` generate integer x coordinates. `imshow(image)` creates an
Image layer. `vbar(values)` and `hbar(values)` generate positions, while
`vbar(x, height)` and `hbar(y, width)` accept explicit positions.

## Embedded in napari

Install napari-plot and open napari. Use `Plugins > napari-plot: Plot Widget`
for the plot viewer or `Plugins > napari-plot: Scatter Widget` to compare the
currently displayed slices of two Image layers. The scatter widget supports 2D
and nD images and only plots slices with matching displayed shapes.

The widgets can also be added programmatically:

```python
import napari
from napari_plot import NapariPlotWidget

viewer = napari.Viewer()
viewer.window.add_dock_widget(NapariPlotWidget(viewer))
napari.run()
```

## Layer API

Use the Add Layer menu in the viewer or call the matching method:

```python
viewer.add_line([[0, 0], [1, 2]], color="cyan")
viewer.add_scatter([[0, 0], [2, 1]], face_color="orange")
viewer.add_multi_line([[[0, 0], [1, 1]], [[0, 2], [1, 3]]])
viewer.add_centroids([[1, 2]], size=1)
viewer.add_text([[1, 2]], ["label"], color="white")
viewer.add_region([[1, 2]], orientation="vertical", opacity=0.3)
viewer.add_inf_line([1, 2], orientation="vertical")
viewer.add_bar([3, 1, 4], fill_color="royalblue")
```

Bar data may be a one-dimensional value sequence or `(position, value)` rows.
Set `orientation="horizontal"`, `baseline`, `width`, `fill_color`,
`border_color`, `border_width`, `opacity`, and `visible` as needed. Shift-click
a bar to toggle its selection; `layer.remove_selected()` deletes selected bars.

Text supports one label or one label per coordinate, font size, color,
horizontal and vertical alignment, rotation, and xy offsets.

### Band

Plot a mean tissue profile over a band showing variation across line profiles.
Either bound can be a scalar, such as a zero baseline when shading a peak.

```python
distance = [0, 25, 50, 75, 100]
mean = [0.15, 0.40, 0.72, 0.58, 0.29]
band = viewer.fill_between(
    distance,
    [0.10, 0.28, 0.60, 0.44, 0.21],
    [0.20, 0.52, 0.84, 0.72, 0.37],
    fill_color="cyan",
    opacity=0.25,
    name="Mean +/- SD",
)
viewer.plot(distance, mean, color="cyan", name="Mean")
```

`viewer.add_band(data)` and `band.data` use `(x, y1, y2)` rows. Use strictly
increasing or decreasing x coordinates and place NaN in either bound to break
the fill at a missing sample. Assign new rows to `band.data` to update all
coordinates together.

### Areas

`Areas` fills many regions in one layer, each between a lower and an upper
curve. Pass one `(t, lo, hi)` array per area. With the default `vertical`
orientation `t` is x and the bounds are y values, like `Band`; with
`horizontal` orientation `t` is y and the bounds are x values. Fill and border
colors can be shared or given per area.

```python
grid = np.linspace(-3, 3, 50)
density = np.exp(-(grid**2) / 2) * 0.4
viewer.add_areas(
    [np.column_stack((grid, i - density, i + density)) for i in range(3)],
    orientation="horizontal",
    fill_color=["tab:blue", "tab:orange", "tab:green"],
    name="Violins",
)
```

`Bar` data also accepts optional third and fourth columns with a per-bar
baseline and width, `(position, value, baseline, width)`, which is how stacked
histograms and box bodies are drawn.

### Error bars

Add asymmetric measurement intervals to calibration points. Supply lower and
upper offsets as two rows, in the same units as the corresponding axis.

```python
concentration = [1, 2, 4]
intensity = [12, 23, 45]
errors = viewer.errorbar(
    concentration,
    intensity,
    yerr=[[1, 2, 4], [2, 3, 6]],
    cap_size=6,
    color="orange",
    name="Measurement intervals",
)
viewer.scatter(concentration, intensity, face_color="orange", name="Standards")
```

`xerr` and `yerr` accept a scalar, one symmetric offset per point, or a
`(2, N)` array of lower and upper offsets. Leave either argument out to omit
that axis. `viewer.add_error_bar(data)` and `errors.data` use
`(x, y, x_minus, x_plus, y_minus, y_plus)` rows with paired NaNs for an
omitted interval. Set `width` and `cap_size` in screen pixels. Set
`cap_size=0` to hide the caps.

### 2D vectors

Overlay registration residuals on an image with napari's native Vectors
layer. Each vector has a `(y, x)` start and a `(dy, dx)` displacement.
With `length=1`, the endpoint is the start plus the displacement.

```python
import numpy as np

viewer.add_image(np.zeros((30, 40)), units=("um", "um"))
viewer.add_vectors(
    np.array([[[10, 20], [3, -5]], [[18, 30], [-2, 4]]]),
    name="Registration residuals",
    vector_style="arrow",
    edge_color="cyan",
    length=1,
    units=("um", "um"),
)
```

### Rectangles

Use Rectangles to display windows in plot coordinates such as retention time
on x and mass-to-charge ratio on y:

```python
peaks = viewer.add_rectangles(
    [[315.5, 521.274], [418.1, 610.305]],
    height=[0.012, 0.008],
    width=[7.0, 10.0],
    outline_width=2,
    outline_color=["cyan", "orange"],
    show_markers=True,
    marker_size=6,
    marker_color="white",
    marker_symbol=["disc", "diamond"],
    text=["Peak A", "Peak B"],
    text_offset=(1.0, 0.002),
)
```

Geometry dimensions are in axis units. Outline width and marker size are in
screen pixels. Set `show_rectangles`, `show_markers`, and `show_text`
independently in the layer controls or from Python. Set `text_color` or
`text_size` to style the labels. Use `peaks.set_data(centers, height, width)`
to replace all geometry at once. `peaks.data` holds [x, y, height, width]
rows. Per-row styles and labels follow row order when you replace the data.

## Layer groups

Layers can share a group ID using metadata, whether they are napari-plot custom
layers or native napari layers. Layers with the same string ID belong to the
same group. An absent key or `None` means the layer is ungrouped. Enable
**Group by layer metadata** in the tiled grid button right-click menu
to overlay members of each group in one grid cell. Ungrouped visible layers each
get their own cell. Grid mode must also be enabled.

Select two or more layers and choose **Group Layers** from the layer-list
right-click menu to create a named group. Choose **Add to Group** to assign the
selection to an existing group in this viewer, or **Ungroup Layers** to clear
membership. These commands affect the selected layers. Hover over a grouped
layer to see its group ID.

Assign a new metadata dictionary to emit napari's metadata event and update the grid.

```python
custom_layer.metadata = {**custom_layer.metadata, "napari_plot.group": "my-group"}
native_layer.metadata = {**native_layer.metadata, "napari_plot.group": "my-group"}
custom_layer.metadata = {**custom_layer.metadata, "napari_plot.group": None}  # clear the group
```

## Statistical plots

`napari_plot.stats` provides seaborn-style plots built from the layers above.
Each function takes the viewer first and is also available as a viewer method.
Single-cell functions return the list of layers they created. Inputs follow seaborn:
long-form DataFrames with `x`, `y` and `hue` column names, wide-form tables
(dict, 2D array or DataFrame columns become categories), or plain arrays.
Estimators, palettes, KDE, histogram bins, letter values, beeswarm layout and
heatmap color limits are computed by seaborn itself.

```python
viewer = napari_plot.Viewer()
viewer.boxplot(tips, x="day", y="total_bill", hue="smoker")
```

Plot helpers that can create multiple layers assign a fresh group ID to all
their layers, even when the chosen options produce only one layer. Pass
`group="my-group"` to share an ID across calls or attach a rug to an existing
plot. This applies to `relplot` when `kind="line"`. Standalone `scatterplot`
layers can be grouped through metadata or the layer-list menu.

| Plot | Function | Layers |
| --- | --- | --- |
| Box plot | `boxplot` | Bar boxes, MultiLine whiskers/medians, Scatter fliers |
| Letter-value plot | `boxenplot` | Bar boxes, MultiLine medians, Scatter outliers |
| Violin plot | `violinplot` (`split`, `inner`) | Areas bodies, MultiLine/Scatter inner marks |
| Grouped bar plot | `barplot` | Bar per hue level, ErrorBar intervals |
| Strip / swarm plot | `stripplot`, `swarmplot` | Scatter per hue level |
| Density | `kdeplot` | MultiLine curves, optional Areas fill |
| Histogram | `histplot` (`multiple`, `stat`, `kde`) | Bar per hue level, optional MultiLine KDE |
| Rug plot | `rugplot` (`x`, `y`, `height`) | MultiLine observation ticks along each supplied axis |
| Classic distplot | `distplot` | histogram + KDE + optional rug |
| Heatmap | `heatmap` (`annot`, `center`, `mask`) | Image, optional Text annotations |
| Clustered heatmap | `clustermap` | Image, MultiLine dendrograms in the margins |
| Relational | `scatterplot`, `lineplot`, `relplot` | Scatter; MultiLine lines with Areas or ErrorBar intervals |

Categorical plots label the categorical axis with category names, and plots
with `hue` show a legend. `swarmplot` computes positions for the canvas size
at call time. `heatmap` draws the first row at the top by flipping the image.

`displot`, `catplot`, and `lmplot` split a table into grid cells using `row` and
`col`. `pairplot` compares numeric variables across a matrix of plots. These
functions return a grid whose `.layers` contains the created layers. `pairplot`
returns a `PairGrid`, a `FacetGrid` subclass.

```python
facets = viewer.catplot(tips, x="day", y="total_bill", col="smoker", kind="box")
facets.set_axis_labels(y_var="Total bill")
```

Use `PairGrid` to map different functions to each region.

```python
from napari_plot.stats import PairGrid, histplot, kdeplot, scatterplot

grid = PairGrid(viewer, data, hue="species")
grid.map_upper(scatterplot).map_lower(kdeplot).map_diag(histplot)
```

Callbacks receive a staging viewer and the table as `data`, with column names as
`x` and `y`. Diagonal callbacks receive `x` only. Mapping methods can be chained.

`jointplot` draws a bivariate plot with marginal distributions and returns a
`JointGrid`. To build the layout manually, use `JointGrid(viewer, top=True,
right=True, ratio=5)`. Set either marginal to `False` to omit it. Use
`grid.add_layer(layer, panel="top")` or `panel="right"` to place a new or
existing layer in a marginal. All panels use the viewer's layer list. The top
panel shares x limits with the main plot, and the right panel shares y limits.

Keep the layer handles to update each plot after setup. The line layers
created by `viewer.plot()` store `(x, y)` rows.

```python
import numpy as np
from napari_plot import JointGrid

main = viewer.plot(x, y)
grid = JointGrid(viewer)
top = grid.add_layer(viewer.plot(x, x_summary), panel="top")
right = grid.add_layer(viewer.plot(y_summary, y), panel="right")

top.data = np.column_stack((x, new_x_summary))
grid.set_axis_labels(y_var="Count", panel="top", visible=False)
```

Pass `visible=True` to show a panel's labels again. Ticks and axis lines stay
visible. `set_axis_labels()` targets the main plot by default.

Use `viewer.rugplot(data, x="total_bill")` to mark observations along the bottom
of a distribution plot. Supply `y` to mark observations along the left side as
well. `height` sets tick length as a fraction of the perpendicular axis span
when the plot is created.

## Axes

Open Axis Controls from the toolbar to show or hide axes and choose linear,
logarithmic, or categorical scales. Category labels are entered in display
order. The same settings are available from Python:

```python
viewer.axis.x_label = "time (s)"
viewer.axis.y_label = "intensity"
viewer.axis.x_scale = "log"

viewer.axis.x_categories = ("control", "treated", "recovery")
# Setting categories also changes the scale to categorical.
```

Logarithmic values must be positive. For API-specific labels, a callable tick
formatter remains supported:

```python
viewer.axis.y_tick_formatter = lambda value: f"{value:.1f} mV"
```

Callable formatters are runtime objects and are intentionally not exposed as
serializable UI settings.

## Legend

The canvas legend lists named, visible plot layers and updates as layers are
added, removed, renamed, restyled, reordered, or hidden. Click a legend row to
hide its source layer; use the layer list to show it again. Left-click the
legend toolbar button to show or hide the overlay and right-click it to change
placement, colors, spacing, and source synchronization.

In grid mode, each cell shows legend rows for its layers by default. Rows
without a layer name appear in every cell, and explicit rows without a matching
grid cell appear in the first cell. Set `viewer.legend.gridded = False` to keep
one combined legend. Outside grid mode there is always one combined legend.

```python
viewer.legend.visible = True
viewer.legend.position = "top_right"
viewer.legend.font_size = 12
```

Positions are `top_left`, `top_center`, `top_right`, `bottom_left`,
`bottom_center`, and `bottom_right`. Explicit and Points-derived legends are
also supported:

```python
viewer.set_legend([
    {"label": "control", "marker": "disc", "color": "royalblue"},
    {"label": "treated", "marker": "square", "color": "orange"},
])

# Restore automatic entries from visible plot layers.
viewer.set_legend_from_layers(sync=True)

# Or derive categories from a napari Points property.
viewer.set_legend_from_points(points, label_property="class", sync=True)
```

## Interaction

- Use the toolbar tools for automatic, box, horizontal, or vertical zoom.
- Use rectangle, polygon, or lasso selection for compatible data layers.
- Shift-click Region, InfLine, or Bar elements for element-level selection.
- Use layer controls to change styles, visibility, ordering, and data-specific settings.
- Use the Add Layer menu for every custom plotting layer plus napari Points and Shapes.

## More examples

The repository's [examples directory](https://github.com/lukasz-migas/napari-plot/tree/main/examples)
contains executable examples for text, logarithmic and categorical axes, bars,
images, live updates, and all custom layers. These examples are run by the test
suite to keep the documented workflows current.

## Reference marks and text

Use `viewer.stem(x, y)` to add vertical Centroids from a baseline. For multiple
curves in one layer, call `viewer.add_multi_line({"xs": [x1, x2], "ys": [y1, y2]})`.
Reference lines made with `axhline` or `axvline` are InfLine layers. Spans made
with `axhspan` or `axvspan` are Region layers.

```python
viewer.axvline(4, color="white", line_style="dashed")
viewer.axhspan(2, 3, color="cyan", opacity=0.2)
viewer.text(4, 3, "Threshold")
viewer.annotate("Peak", xy=(6, 5), xytext=(7, 6), color="orange")
```

`text` and `annotate` add a Text layer at plot coordinates. An annotation with a
different label position adds a separate Line layer for the arrow. For text
fixed to a corner of the viewport, use `add_text_overlay`.

## Select data

Select the box, lasso, or polygon tool in the toolbar and finish the shape.
`viewer.drag_tool.vertices` continues to provide the shape vertices in
`(y, x)` world coordinate order. Scatter, Line, MultiLine, Bar and Centroids
layers record matching element indices in `selected_data` when the layer is
visible and selected in the layer list. A MultiLine index
identifies a whole line and a Line index identifies a vertex.

```python
def report_selection(event):
    for layer, indices in event.value.items():
        print(layer.name, sorted(indices))

viewer.events.selection.connect(report_selection)
```

In grid mode the selection applies to the cell where the interaction occurred.

## Axes and color scales

```python
viewer.xlim = (10, 0)  # Reversed axis.
viewer.margins = (0.05, 0.1)  # Fractions of the data extent.
viewer.axis.x_minor_ticks = False
viewer.axis.y_tick_notation = "scientific"
viewer.axis.y_tick_formatter = None  # Restore the built-in formatter.
viewer.grid_lines.minor = True
```

Turn off `viewer.autoscale` to prevent automatic fits. `viewer.reset_view()`
still fits the current data on demand. Datetime axes label numeric seconds
relative to `viewer.axis.x_datetime_origin` or `y_datetime_origin`. Use
`napari_plot.components.axis.datetime_axis_values(timestamps, origin=origin)`
to convert datetimes into plot coordinates. A nearby origin preserves precision
for short intervals. The `power` scale uses `x_power` or `y_power` and preserves
the sign of each coordinate.

```python
viewer.canvas.grid.enabled = True
viewer.canvas.grid.sharey = False
cell = viewer.canvas.grid.cell(0, 0)
cell.y_label = "Intensity"
cell.ylim = (0, 1000)
viewer.set_colorbar_from_layer(image, "Counts", cell=(0, 0), position="bottom", norm="log")
```

An Image colorbar follows its colormap, contrast limits and gamma. A Scatter
colorbar follows its face colormap and face contrast limits. Logarithmic spacing
applies to strictly positive limits. Omit `cell` for a figure-level colorbar.
Use `colorbar_for_cell(row, column)` to configure a specific cell, or right-click
the toolbar colorbar button for placement and source settings.

Legends and axes inherit colors from the viewer theme. Passing a color overrides
the theme. Set the color back to `None` to resume inheritance. To place a legend
to the right of the plot, use `set_legend_from_layers(title="Series", ncols=2, outside=True)`.

## Exporting figures and saving sessions

```python
viewer.screenshot("current-view.png")
viewer.export_figure("full-extent.png", dpi=300)
viewer.export_vector("full-extent.svg")  # Also accepts .pdf.
viewer.export_csv("samples", "samples.csv")
viewer.save_session("experiment.napari-plot")
```

`screenshot` captures the current view. `export_figure` and `export_vector`
fit the plotted data temporarily and restore the view afterward. The SVG and
PDF exporters preserve supported strokes, fills, markers, and text as vector
geometry. Image layers are embedded as bitmap data. Use a screenshot to
retain the exact appearance of OpenGL-specific styling.

Session files include the layer data, their plotting attributes, axis and grid
settings, the view range, and the legend and color scale. Custom Python tick
formatter callbacks stay in the script that defines them. Use
`viewer.load_session("experiment.napari-plot")` to replace the current plot.
The File menu provides figure, CSV and session commands. You can drag a session,
a two-column CSV (`x,y` for Line or `y,x` for Scatter), or a file supported by
an installed napari reader into the viewer.
