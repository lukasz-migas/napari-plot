# Quickstart

napari-plot uses napari layers to build interactive one dimensional plots. Use
the standalone viewer for a focused plotting window, or dock the same viewer in
napari.

## Install

Use Python 3.11 or later and choose one Qt6 backend. Install the package and
backend together:

```shell
pip install "napari-plot[pyqt6]"
```

For PySide6, install `napari-plot[pyside6]` instead. The `stats` extra adds
seaborn-style statistical plots:

```shell
pip install "napari-plot[pyqt6,stats]"
```

## Make a plot

Create a viewer, add layers, then start the Qt event loop. Keep the viewer in a
variable while the window is open.

```python
import numpy as np
import napari_plot

viewer = napari_plot.Viewer(title="Signal")
x = np.linspace(0, 2 * np.pi, 500)
y = np.sin(x)

viewer.plot(x, y, name="signal", color="cyan")
viewer.scatter(x[::25], y[::25], name="samples", size=8)
viewer.axis.x_label = "Time (s)"
viewer.axis.y_label = "Amplitude"
viewer.legend.visible = True

napari_plot.run()
```

`plot(y)` and `scatter(y)` use integer sample positions for x. The returned
objects are layer handles, so you can update data and properties later:

```python
line = viewer.plot(y, name="live signal")
line.data = np.column_stack((np.arange(len(y)), y * 0.5))
line.visible = False
```

## Use napari

Open napari and choose **Plugins > napari-plot: Plot Widget**. You can also add
the plot viewer from Python:

```python
import napari
from napari_plot import NapariPlotWidget

viewer = napari.Viewer()
viewer.window.add_dock_widget(NapariPlotWidget(viewer))
napari.run()
```

The Scatter Widget compares displayed slices from two napari Image layers. The
two slices need matching displayed shapes.

## Next steps

- Use the [layers guide](layers.md) to choose a layer and understand its data.
- Run an [example](examples.md) with `uv run --extra pyqt6 python examples/add_scatter.py`.
- Read [in-depth explanations](explanations.md) for axes, selection, grids, and files.

For development, clone the repository and install the selected extras with
`uv sync --extra pyqt6 --extra docs`.
