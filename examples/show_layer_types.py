"""Display image and 1d plot."""

import numpy as np

import napari_plot

N_POINTS = 1000
N_MIN = 0
N_MAX = 300


def add_line():
    """Line plot"""
    x = np.arange(N_POINTS)
    y = np.random.randint(N_MIN, N_MAX, N_POINTS)
    viewer1d.add_line(np.c_[x, y], name="Line", visible=True)


def add_centroids():
    """Centroids plot"""
    x = np.arange(N_POINTS)
    y = np.random.randint(N_MIN, N_MAX, N_POINTS)
    viewer1d.add_centroids(np.c_[x, y], color=(1.0, 0.0, 1.0, 1.0), name="Centroids (x)", visible=True)
    viewer1d.add_centroids(
        np.c_[y, x],
        color=(1.0, 0.0, 1.0, 1.0),
        name="Centroids (y)",
        visible=True,
        orientation="horizontal",
    )


def add_scatter():
    """Centroids plot"""
    x = np.random.randint(N_MIN, N_MAX, N_POINTS // 2)
    y = np.random.randint(N_MIN, N_POINTS, N_POINTS // 2)
    viewer1d.add_scatter(np.c_[y, x], size=5, name="Scatter", visible=True)


def add_region():
    """Region plot"""
    regions = [
        ([25, 50], "vertical"),
        ([50, 400], "horizontal"),
        ([80, 90], "vertical"),
    ]
    viewer1d.add_region(regions, color=["red", "green", "cyan"], opacity=0.5, name="Spans", visible=True)


def add_infline():
    """Inf line plot"""
    viewer1d.add_inf_line(
        [50, 15, 250],
        orientation=["vertical", "vertical", "horizontal"],
        width=3,
        color=["red", "orange", "green"],
        name="Infinite Line",
        visible=True,
    )


viewer1d = napari_plot.Viewer()

add_line()
add_centroids()
add_region()
add_scatter()
add_infline()

if __name__ == "__main__":
    napari_plot.run()
