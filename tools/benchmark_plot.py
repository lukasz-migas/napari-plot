# ruff: noqa: INP001
"""Measure common large-data model operations with ``uv run python tools/benchmark_plot.py``."""

from argparse import ArgumentParser
from collections.abc import Callable
from itertools import cycle
from statistics import median
from timeit import repeat

import numpy as np

from napari_plot.components.viewer_model import ViewerModel


def _workloads(count: int) -> dict[str, Callable[[], object]]:
    x = np.linspace(0, 100, count)
    y = np.sin(x)
    points = np.column_stack((y, x))
    lines = {"x": x, "ys": [y, np.cos(x), np.sin(x + 1), np.cos(x + 1)]}
    next_frame = {"x": x, "ys": [amplitude * 1.01 for amplitude in lines["ys"]]}

    viewer = ViewerModel()
    viewer.add_scatter(points, size=3)
    multiline_viewer = ViewerModel()
    multiline = multiline_viewer.add_multi_line(lines)
    polygon = np.array([[-0.5, 40], [0.5, 40], [0.5, 60], [-0.5, 60]])
    selections = cycle([polygon, polygon + (0, 10)])
    frames = cycle([next_frame, lines])

    def stream_vertices() -> np.ndarray:
        multiline.stream(next(frames))
        return multiline._data_view.get_display_data()

    return {
        "construct Scatter": lambda: ViewerModel().add_scatter(points, size=3),
        "select Scatter with box": lambda: viewer._select_data(next(selections)),
        "stream four MultiLine traces": stream_vertices,
    }


def main() -> None:
    """Report median time per operation over several independent batches."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--points", type=int, default=100_000, help="Samples per layer or trace.")
    parser.add_argument("--repeat", type=int, default=5, help="Number of batches to time.")
    parser.add_argument("--number", type=int, default=5, help="Operations per batch.")
    args = parser.parse_args()
    if min(args.points, args.repeat, args.number) < 1:
        parser.error("points, repeat, and number must be positive")

    print(f"{args.points:,} points per trace, {args.repeat} batches of {args.number}")
    for name, run in _workloads(args.points).items():
        run()  # initialize dependencies before measuring steady-state work
        samples = repeat(run, repeat=args.repeat, number=args.number)
        print(f"{name:<30} {median(samples) * 1000 / args.number:>10.3f} ms")


if __name__ == "__main__":
    main()
