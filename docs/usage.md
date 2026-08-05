# Usage

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
