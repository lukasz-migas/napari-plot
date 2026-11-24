# Layers guide

Each plotted object is a napari layer. The layer list controls visibility,
ordering, and opacity, while the layer controls panel exposes properties for
the selected layer. Python methods return the created layer, which you can keep
to update its data or style.

## Choose a layer

| Layer | Use it for | Input shape or helper |
| --- | --- | --- |
| Line | A connected sequence of measurements | `(x, y)` rows; `viewer.plot(x, y)` |
| Scatter | Independent observations | napari point coordinates `(y, x)`; `viewer.scatter(x, y)` accepts x then y |
| MultiLine | Several connected series in one layer | A list of lines or `{"xs": [...], "ys": [...]}` |
| Centroids | Vertical stems or point markers | Point coordinates; `viewer.stem(x, y)` |
| Bar | Histograms and categorical summaries | Values or rows of `(position, value)` |
| Band | A filled interval around one curve | `(x, lower, upper)` rows; `viewer.fill_between(...)` |
| Areas | Several filled intervals in one layer | One `(t, lower, upper)` array per area |
| ErrorBar | Measurement uncertainty around points | `viewer.errorbar(x, y, xerr=..., yerr=...)` |
| Region | A span across one axis | Bounds and horizontal or vertical orientation |
| InfLine | A line across the plot | `viewer.axhline(y)` or `viewer.axvline(x)` |
| Rectangles | Windows around points or regions | Centers with per-rectangle height and width |
| Text | Labels at data coordinates | Coordinates and labels |
| Image | A 2D image in plot coordinates | `viewer.imshow(image)` |
| Vectors | Displacements over an image | napari vector data in `(y, x)` order |

Custom plot coordinates use x then y in convenience methods such as `plot` and
`scatter`. Several lower-level layer constructors follow napari's coordinate
order and expect `(y, x)`. The returned layer's `data` property follows that
layer's documented shape.

## Lines and points

`plot` creates a Line. One-dimensional input generates x coordinates from zero;
two inputs use the supplied x and y values.

```python
line = viewer.plot(time, intensity, name="spectrum", color="royalblue", width=2)
line.data = np.column_stack((time, corrected_intensity))
```

`scatter` follows the same convenience calling pattern. Color can be fixed for
all markers or mapped from values with the layer's colormap options.

```python
points = viewer.scatter(time, intensity, name="peaks", size=7, face_color="orange")
```

Use MultiLine when a set of series should share one layer entry. Use separate
Line layers when each series needs its own legend row or visibility control.

## Intervals and reference marks

Band fills between two bounds on a shared x grid. Either bound may be a scalar.
The x coordinates must be monotonic. A NaN in either bound breaks the filled
region at that sample.

```python
band = viewer.fill_between(
    time,
    lower,
    upper,
    fill_color="cyan",
    opacity=0.25,
    name="uncertainty",
)
```

ErrorBar accepts a scalar error, an array with one error per point, or a `(2, N)`
array of lower and upper offsets. `cap_size` and stroke width are measured in
screen pixels.

```python
errors = viewer.errorbar(
    concentration,
    signal,
    yerr=[lower_error, upper_error],
    cap_size=6,
    color="orange",
)
```

Use `axvline`, `axhline`, `axvspan`, and `axhspan` for common reference marks.
`Region` and `InfLine` layers can also be added directly when you need a
collection of spans or lines in one layer.

## Bars and areas

For vertical bars, pass heights alone or explicit x positions and heights.
Horizontal bars use y positions and lengths. `baseline` sets the starting value.
At the layer level, Bar data can include baseline and width per bar.

```python
bars = viewer.vbar(
    [0, 1, 2],
    [12, 18, 14],
    fill_color=["royalblue", "orange", "seagreen"],
)
viewer.axis.x_categories = ("control", "treated", "recovery")
```

Areas stores multiple filled ranges in one layer. In vertical orientation, each
array contains `(x, lower, upper)` values. Horizontal orientation treats the
first column as y and the bounds as x coordinates.

```python
areas = viewer.add_areas(
    [np.column_stack((x, center - spread, center + spread))],
    orientation="vertical",
    fill_color="royalblue",
    opacity=0.3,
)
```

## Labels and rectangles

Text places one or more labels at plot coordinates. `annotate` can add a leader
line from the label to a data point. Use `add_text_overlay` for text attached to
the viewport rather than to data coordinates.

Rectangles use plot units for their geometry. Outline widths and marker sizes
use screen pixels. You can show or hide rectangles, corner markers, and labels
independently.

```python
rectangles = viewer.add_rectangles(
    [[315.5, 521.274]],
    height=[0.012],
    width=[7.0],
    outline_color="cyan",
    text=["Peak A"],
)
```

## Images and vectors

`imshow` uses napari's Image layer API. For images with physical coordinates,
pass scale, translate, and units as supported by napari. Vectors use napari's
native vector representation: each row contains a `(y, x)` start and a `(dy,
dx)` displacement.

```python
viewer.add_vectors(
    np.array([[[10, 20], [3, -5]]]),
    vector_style="arrow",
    length=1,
    edge_color="cyan",
)
```

## Layer data and selection

Keep a reference to a returned layer when data will change. Assigning a new
array to `layer.data` updates the display. Some layers have structured data;
for example, Band stores `(x, lower, upper)` rows and Rectangles stores
`[x, y, height, width]` rows. Check the relevant layer section before changing
its data.

Selection tools report indices for supported layers through `selected_data`.
For Line, an index identifies a vertex; for MultiLine, it identifies an entire
curve. See [navigation and selection](explanations.md#navigation-and-selection) for
callbacks and interaction details.
