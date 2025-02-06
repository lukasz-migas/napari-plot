"""Example showing how to use the MultiLine layer type.

The MultiLine layer is implemented to enable better performance when plotting multiple lines of long length.
In the example below we are plotting several long lines with no noticeable performance drop.
"""

import numpy as np

import napari_plot

image = np.random.randint(0, 255, (100, 100))

viewer1d = napari_plot.Viewer()
viewer1d.add_image(image)

# ensure that pixels remain square
viewer1d.camera.aspect = 1

if __name__ == "__main__":
    napari_plot.run()
