"""Hierarchically clustered heatmap with dendrograms drawn in the canvas margins."""

import numpy as np
import pandas as pd

import napari_plot

rng = np.random.default_rng(7)
groups = np.repeat([0, 1, 2], 6)
profiles = rng.normal(size=(3, 10))
matrix = profiles[groups] + rng.normal(scale=0.4, size=(18, 10))
frame = pd.DataFrame(
    matrix,
    index=pd.Index([f"sample {i}" for i in range(18)], name="sample"),
    columns=pd.Index([f"gene {j}" for j in range(10)], name="gene"),
)

viewer = napari_plot.Viewer()
viewer.clustermap(frame, z_score=1, center=0, cmap="vlag")

if __name__ == "__main__":
    napari_plot.run()
