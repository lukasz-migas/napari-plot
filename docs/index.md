# napari-plot

napari-plot is an interactive, GPU-accelerated plotting viewer built with Qt,
VisPy, and napari's layer model. It can run as a standalone plotting application
or as a dock widget inside napari.

## Installation

napari-plot supports Python 3.11 and later.

```shell
pip install "napari-plot[all]"
```

For a local development checkout:

```shell
git clone https://github.com/lukasz-migas/napari-plot.git
cd napari-plot
pip install -e ".[all]"
```

## Quick start

```python
import numpy as np
import napari_plot

viewer = napari_plot.Viewer()
x = np.linspace(0, 2 * np.pi, 500)
viewer.plot(x, np.sin(x), name="signal", color="cyan")
viewer.scatter(x[::25], np.sin(x[::25]), name="samples")
viewer.legend.visible = True
napari_plot.run()
```

The lower-level layer API remains available when detailed control is needed:

```python
viewer.add_region([[1.0, 2.0]], orientation="vertical", name="interval")
viewer.add_text([[3.0, 0.5]], ["peak"], color="yellow")
```

See the [usage guide](usage.md) for standalone and embedded examples,
interactions, axis scales, and all supported layer types. The [API reference](api.md)
summarizes the stable public entry points.

## Highlights

- Line, Scatter, MultiLine, Centroids, Text, Region, InfLine, and Bar layers
- Linear, logarithmic, and categorical axes
- Interactive selection, zoom, layer controls, and legend
- Image display and a scatter-from-image dock widget
- Concise `plot`, `scatter`, `imshow`, `hbar`, and `vbar` helpers
- Full access to the lower-level `add_*` layer methods

Contributions and bug reports are welcome in the
[GitHub repository](https://github.com/lukasz-migas/napari-plot).
