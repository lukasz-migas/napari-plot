"""Compare measurements across batches with regression, distributions, or categories."""

from argparse import ArgumentParser
from itertools import product

import numpy as np
import pandas as pd

import napari_plot

KINDS = ("regression", "ecdf", "point", "count", "pair", "joint-hist", "joint-kde")
PALETTE = {"Control": "steelblue", "Treated": "orange"}


def make_plot(kind: str = "regression") -> napari_plot.Viewer:
    """Draw one of the faceted examples using reproducible measurements."""
    rng = np.random.default_rng(41)
    frames = []
    for batch, treatment in product(("First", "Second"), PALETTE):
        count = 42 if treatment == "Control" else 32
        dose = rng.uniform(0, 12, count)
        slope = 0.5 if treatment == "Treated" else 0.25
        offset = 1.5 if batch == "Second" else 0.0
        response = 2 + offset + slope * dose + rng.normal(0, 0.5, count)
        frames.append(pd.DataFrame({"batch": batch, "treatment": treatment, "dose": dose, "response": response}))
    data = pd.concat(frames, ignore_index=True)

    viewer = napari_plot.Viewer(title=f"Batch measurements ({kind})")
    viewer.window.resize(1080, 700)
    viewer.margins = (0.05, 0.06)
    match kind:
        case "regression":
            facets = viewer.lmplot(
                data,
                x="dose",
                y="response",
                col="batch",
                hue="treatment",
                palette=PALETTE,
                n_boot=100,
                seed=41,
            )
            facets.set_axis_labels(y_var="Measured response")
        case "ecdf":
            viewer.displot(data, x="response", col="batch", hue="treatment", palette=PALETTE, kind="ecdf")
        case "point":
            viewer.catplot(data, x="treatment", y="response", col="batch", kind="point", errorbar="se")
        case "count":
            viewer.catplot(data, x="treatment", col="batch", kind="count")
        case "pair":
            viewer.pairplot(
                data,
                vars=["dose", "response"],
                hue="treatment",
                diag_kind="hist",
                plot_kws={"palette": PALETTE},
                diag_kws={"palette": PALETTE},
            )
        case "joint-hist":
            grid = viewer.jointplot(data, x="dose", y="response", kind="hist", joint_kws={"bins": 12})
            # Add a custom reference line to the top marginal.
            from napari_plot.layers import Line

            grid.add_layer(Line([[0, 0], [12, 10]], color="orange"), panel="top")
        case "joint-kde":
            viewer.jointplot(
                data,
                x="dose",
                y="response",
                kind="kde",
                joint_kws={"gridsize": 64},
                marginal_kws={"gridsize": 64},
            )
        case _:
            raise ValueError(f"Choose one of {KINDS}.")
    viewer.canvas.grid.spacing = 10
    if viewer.legend.visible:
        viewer.legend.title = "Treatment"
        viewer.legend.position = "bottom_right"
        viewer.legend.gridded = False
    return viewer


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=KINDS, default="regression")
    viewer = make_plot(parser.parse_args().kind)
    napari_plot.run()
else:
    viewer = make_plot()
