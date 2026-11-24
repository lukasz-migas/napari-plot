"""Split violin plots
================

Compare two hue levels within each category.

.. tags:: statistical-plots, violin"""

import numpy as np
import pandas as pd

import napari_plot

rng = np.random.default_rng(1)
n = 400
frame = pd.DataFrame(
    {
        "condition": rng.choice(["control", "low dose", "high dose"], n),
        "sex": rng.choice(["female", "male"], n),
    }
)
shift = frame["condition"].map({"control": 0, "low dose": 1.5, "high dose": 3})
frame["response"] = rng.normal(shift, 1 + (frame["sex"] == "male"))

viewer = napari_plot.Viewer()
viewer.violinplot(frame, x="condition", y="response", hue="sex", split=True, inner="quart")

if __name__ == "__main__":
    napari_plot.run()
