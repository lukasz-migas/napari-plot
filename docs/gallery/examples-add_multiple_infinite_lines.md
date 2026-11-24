# Multiple infinite lines

Multiple infinite lines in a single layer.

**Tags:** `lines`

![Multiple infinite lines example screenshot](../assets/gallery/examples-add_multiple_infinite_lines.jpg)

[View the source file on GitHub](https://github.com/lukasz-migas/napari-plot/blob/main/examples/add_multiple_infinite_lines.py)

## Python example

```python
"""Multiple infinite lines
===========================

Multiple infinite lines in a single layer.

.. tags:: lines
"""

import numpy as np

import napari_plot

viewer1d = napari_plot.Viewer()
viewer1d.add_line(np.c_[np.arange(1000), np.random.default_rng().integers(0, 1000, 1000)], name="line")

# You can add infinite lines providing different orientations and colors
layer = viewer1d.add_inf_line(
    [50, 140, 250],
    orientation=["vertical", "vertical", "horizontal"],
    width=3,
    color=["red", "yellow", "green"],
    name="Infinite Line",
)
if __name__ == "__main__":
    napari_plot.run()
```
