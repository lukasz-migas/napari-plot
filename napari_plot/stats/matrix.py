"""Matrix plots: annotated heatmap and hierarchically clustered heatmap."""

from __future__ import annotations

import typing as ty

import numpy as np
import pandas as pd

from napari_plot.stats import _common as cm
from napari_plot.stats._palette import colormap_from_mpl, to_rgba

if ty.TYPE_CHECKING:
    from napari.layers import Layer

    from napari_plot.components.viewer_model import ViewerModel


def _tick_labels(ticks: ty.Any, labels: ty.Sequence[str], count: int) -> list[str] | None:
    """Expand seaborn tick positions (cell centers at i + 0.5) to one label per cell, or None to hide."""
    if isinstance(ticks, str):  # "auto": label every cell
        return [str(label) for label in labels]
    if not len(ticks):
        return None
    expanded = [""] * count
    for tick, label in zip(ticks, labels, strict=False):
        expanded[round(tick - 0.5)] = str(label)
    return expanded


def heatmap(
    viewer: ViewerModel,
    data: ty.Any,
    *,
    vmin: float | None = None,
    vmax: float | None = None,
    cmap: ty.Any = None,
    center: float | None = None,
    robust: bool = False,
    annot: ty.Any = None,
    fmt: str = ".2g",
    annot_size: float | None = None,
    annot_color: ty.Any = None,
    mask: ty.Any = None,
    xticklabels: ty.Any = True,
    yticklabels: ty.Any = True,
    name: str = "heatmap",
) -> list[Layer]:
    """Draw a matrix as a color-encoded image, optionally annotating each cell with its value.

    Rows are drawn top to bottom like seaborn; DataFrame index/columns label the axes.

    Parameters
    ----------
    viewer : ViewerModel
        Viewer to draw on.
    data : 2D array-like or DataFrame
        Matrix to draw.
    vmin, vmax : float, optional
        Colormap limits (data range, or 2nd/98th percentiles with ``robust``).
    cmap : str, list or matplotlib colormap, optional
        Colormap (seaborn's ``rocket``, or ``icefire`` when ``center`` is set).
    center : float, optional
        Value at the center of a diverging colormap.
    robust : bool
        Use robust quantiles for the default limits.
    annot : bool or array-like, optional
        Annotate cells with the data (True) or with values of an array of the same shape.
    fmt : str
        Format spec for annotations.
    annot_size : float, optional
        Annotation font size in screen points; by default derived from the cell size on the current canvas.
    annot_color : color, optional
        Annotation color; by default chosen per cell for contrast.
    mask : bool array-like, optional
        Cells where True are not drawn or annotated.
    xticklabels, yticklabels : bool, int, list or "auto"
        Tick labels as in seaborn (int labels every n-th cell).
    name : str
        Prefix for created layer names.

    Returns
    -------
    list of Layer
        Created layers in drawing order.
    """
    from napari_plot.stats._seaborn import _HeatMapper, relative_luminance

    mapper = _HeatMapper(
        data, vmin, vmax, cmap, center, robust, annot, fmt, None, False, None, xticklabels, yticklabels, mask
    )
    values = mapper.plot_data.astype(float).filled(np.nan)
    n_rows, n_cols = values.shape
    low, high = float(mapper.vmin), float(mapper.vmax)
    if high <= low:
        high = low + 1.0
    layers: list[Layer | None] = [
        viewer.add_image(
            values[::-1],  # plot y axis points up, seaborn draws the first row at the top
            colormap=colormap_from_mpl(mapper.cmap),
            contrast_limits=(low, high),
            name=name,
        )
    ]

    if mapper.annot:
        positions, texts, colors = [], [], []
        annot_values = np.asarray(mapper.annot_data)
        for row in range(n_rows):
            for col in range(n_cols):
                value = values[row, col]
                if np.isnan(value):
                    continue
                positions.append((col, n_rows - 1 - row))
                texts.append(("{:" + fmt + "}").format(annot_values[row, col]))
                if annot_color is None:
                    rgba = mapper.cmap((value - low) / (high - low))
                    colors.append("#262626" if relative_luminance(rgba) > 0.408 else "white")
                else:
                    colors.append(annot_color)
        if positions:
            if annot_size is None:
                # Fit the longest label in a cell: the plot uses ~75% of the canvas, digits are ~0.65 em wide plus
                # one em of padding; the 0.4 factor converts to the Text layer's font size (calibrated visually).
                height_px, width_px = viewer._canvas_size
                cell_w, cell_h = 0.75 * width_px / n_cols, 0.75 * height_px / n_rows
                longest = max(len(text) for text in texts)
                fit_px = min(0.6 * cell_h, cell_w / (0.65 * longest + 1.0))
                annot_size = float(np.clip(0.4 * fit_px, 4, 12))
            layers.append(
                viewer.add_text(np.asarray(positions), texts, color=colors, size=annot_size, name=f"{name} annotations")
            )

    x_labels = _tick_labels(mapper.xticks, mapper.xticklabels, n_cols)
    y_labels = _tick_labels(mapper.yticks, mapper.yticklabels, n_rows)
    viewer.axis.x_categories = x_labels
    viewer.axis.y_categories = None if y_labels is None else y_labels[::-1]
    cm.set_axis_labels(viewer, mapper.xlabel, mapper.ylabel)
    created = [layer for layer in layers if layer is not None]
    cm.fit_view(viewer, include=(-0.5, n_cols - 0.5, -0.5, n_rows - 0.5), margin=0)
    return created


def _tree_lines(tree: ty.Any) -> tuple[np.ndarray, np.ndarray]:
    """Return dendrogram link coordinates as (leaf position, normalized height) polylines."""
    leaves = (np.asarray(tree.independent_coord, dtype=float) - 5) / 10
    heights = np.asarray(tree.dependent_coord, dtype=float)
    return leaves, heights / (heights.max() or 1.0)


def clustermap(
    viewer: ViewerModel,
    data: ty.Any,
    *,
    method: str = "average",
    metric: str = "euclidean",
    z_score: int | None = None,
    standard_scale: int | None = None,
    row_cluster: bool = True,
    col_cluster: bool = True,
    row_linkage: np.ndarray | None = None,
    col_linkage: np.ndarray | None = None,
    dendrogram_ratio: float = 0.2,
    tree_color: ty.Any = "lightgray",
    tree_width: float = 1.0,
    name: str = "clustermap",
    **heatmap_kws: ty.Any,
) -> list[Layer]:
    """Draw a hierarchically clustered heatmap with row/column dendrograms in the canvas margins.

    Parameters
    ----------
    viewer : ViewerModel
        Viewer to draw on.
    data : 2D array-like or DataFrame
        Matrix to cluster and draw.
    method, metric : str
        Linkage method and distance metric (scipy).
    z_score, standard_scale : {0, 1}, optional
        Standardize (z-score) or min-max scale rows (0) or columns (1) before clustering.
    row_cluster, col_cluster : bool
        Whether to cluster and draw a dendrogram for rows / columns.
    row_linkage, col_linkage : array, optional
        Precomputed linkage matrices.
    dendrogram_ratio : float
        Dendrogram depth as a fraction of the heatmap height (columns) or width (rows).
    tree_color, tree_width
        Dendrogram line style (width in screen pixels).
    name : str
        Prefix for created layer names.
    **heatmap_kws
        Passed to :func:`heatmap`.

    Returns
    -------
    list of Layer
        Created layers in drawing order.
    """
    from napari_plot.stats._seaborn import ClusterGrid, _DendrogramPlotter

    if z_score is not None and standard_scale is not None:
        raise ValueError("Cannot use both z_score and standard_scale.")
    frame = data if isinstance(data, pd.DataFrame) else pd.DataFrame(np.asarray(data))
    if z_score is not None:
        frame = ClusterGrid.z_score(frame, z_score)
    if standard_scale is not None:
        frame = ClusterGrid.standard_scale(frame, standard_scale)
    n_rows, n_cols = frame.shape

    row_tree = _DendrogramPlotter(frame, row_linkage, metric, method, 0, False, True) if row_cluster else None
    col_tree = _DendrogramPlotter(frame, col_linkage, metric, method, 1, False, False) if col_cluster else None
    row_order = row_tree.reordered_ind if row_tree is not None else list(range(n_rows))
    col_order = col_tree.reordered_ind if col_tree is not None else list(range(n_cols))
    layers = heatmap(viewer, frame.iloc[row_order, col_order], name=name, **heatmap_kws)

    links = []
    if col_tree is not None:  # above the heatmap
        leaves, heights = _tree_lines(col_tree)
        depth = dendrogram_ratio * n_rows
        links += [np.column_stack((x, n_rows - 0.5 + h * depth)) for x, h in zip(leaves, heights, strict=True)]
    if row_tree is not None:  # left of the heatmap; first leaf sits on the top row
        leaves, heights = _tree_lines(row_tree)
        depth = dendrogram_ratio * n_cols
        links += [np.column_stack((-0.5 - h * depth, n_rows - 1 - y)) for y, h in zip(leaves, heights, strict=True)]
    tree = cm.add_segments(viewer, links, "v", color=to_rgba(tree_color), width=tree_width, name=f"{name} dendrograms")
    if tree is not None:
        layers.append(tree)
    cm.fit_view(viewer, include=(-0.5, n_cols - 0.5, -0.5, n_rows - 0.5), margin=0.02)
    return layers
