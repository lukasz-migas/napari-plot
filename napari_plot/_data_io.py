"""Read data into plots and export layer values as CSV."""

from __future__ import annotations

import csv
import os
from collections.abc import Iterable, Sequence
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import numpy as np
from napari.errors import MultipleReaderError, NoAvailableReaderError, ReaderPluginError
from napari.layers import Layer
from napari.layers._source import Source, layer_source

from napari_plot._session import SESSION_SUFFIX
from napari_plot.layers import Areas, Band, Bar, Centroids, ErrorBar, InfLine, Line, MultiLine, Rectangles, Region, Text

if TYPE_CHECKING:
    from napari_plot.components.viewer_model import ViewerModel

TABLE_HEADERS = {
    Line: ("x", "y"),
    Bar: ("position", "value"),
    Centroids: ("position", "value"),
    Band: ("x", "lower", "upper"),
    ErrorBar: ("x", "y", "x_error_lower", "x_error_upper", "y_error_lower", "y_error_upper"),
    Rectangles: ("x", "y", "height", "width"),
}


def export_csv(layer: Layer, path: str | Path) -> None:
    """Write the layer's source data in UTF-8 CSV, one record per sample."""
    data = layer.data
    rows: Iterable[Sequence[Any]]
    if type(layer) in TABLE_HEADERS:
        header = TABLE_HEADERS[type(layer)]
        rows = data
    elif isinstance(layer, InfLine):
        header = ("position", "orientation")
        rows = zip(np.asarray(data).reshape(-1), layer.orientation, strict=True)
    elif isinstance(layer, Region):
        header = ("lower", "upper", "orientation")
        rows = ((*values, orientation) for values, orientation in zip(data, layer.orientation, strict=True))
    elif isinstance(layer, MultiLine):
        header = ("group", "x", "y")
        rows = (
            (index, x, y)
            for index, (xs, ys) in enumerate(zip(data["xs"], data["ys"], strict=True))
            for x, y in zip(xs, ys, strict=True)
        )
    elif isinstance(layer, Areas):
        header = ("group", "position", "lower", "upper")
        rows = ((index, *values) for index, area in enumerate(data) for values in area)
    elif isinstance(layer, Text):
        header = ("x", "y", "text")
        rows = ((*point, text) for point, text in zip(data, layer.text, strict=True))
    elif layer._type_string in ("scatter", "points"):
        header = tuple(f"axis_{index}" for index in range(layer.ndim - 2)) + ("y", "x")
        rows = data
    else:
        # Native napari arrays and ragged geometric data can still be exported as indexed values.
        arrays = (
            [np.asarray(part) for part in data]
            if isinstance(data, (list, tuple)) or getattr(layer, "multiscale", False)
            else [np.asarray(data)]
        )
        dimensions = max((array.ndim for array in arrays), default=0)
        header = ("group", *(f"index_{axis}" for axis in range(dimensions)), "value")
        rows = (
            (group, *index, *("" for _ in range(dimensions - array.ndim)), value)
            for group, array in enumerate(arrays)
            for index, value in np.ndenumerate(array)
        )

    with Path(path).expanduser().open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)


def open_paths(
    viewer: ViewerModel,
    paths: str | Path | Sequence[str | Path],
    *,
    stack: bool | list[list[str]],
    plugin: str | None,
    layer_type: str | None,
    **kwargs: Any,
) -> list[Layer]:
    """Open sessions, two-column CSV plots and files supported by napari reader plugins."""
    from napari.components.viewer_model import _validate_paths_exist
    from napari.plugins import _npe2
    from napari.plugins.io import read_data_with_plugins
    from napari.plugins.utils import get_preferred_reader

    filenames = [os.fspath(paths)] if isinstance(paths, (str, Path)) else [os.fspath(path) for path in paths]
    if not filenames:
        return []
    groups = [filenames] if stack else [[filename] for filename in filenames]
    if isinstance(stack, list):
        groups.extend(stack)

    added = []
    for group in groups:
        _validate_paths_exist(group)
        path = group[0]
        parsed = urlparse(path)
        suffix = Path(parsed.path).suffix.lower()
        if len(group) == 1 and not parsed.netloc and plugin is None and layer_type is None:
            if suffix == SESSION_SUFFIX:
                added = viewer.load_session(path)
                continue
            if suffix == ".csv":
                with Path(path).open(encoding="utf-8-sig", newline="") as stream:
                    rows = [row for row in csv.reader(stream) if row]
                header = [value.strip().lower() for value in rows[0]] if rows else []
                data = None
                if header in (["x", "y"], ["y", "x"]):
                    data = (
                        np.asarray(rows[1:], dtype=float).reshape(-1, 2)
                        if len(rows) == 1
                        else np.asarray(rows[1:], dtype=float)
                    )
                elif rows:
                    with suppress(ValueError):
                        data = np.asarray(rows, dtype=float)
                if data is not None and data.ndim == 2 and data.shape[1] == 2:
                    add = viewer.add_scatter if header == ["y", "x"] else viewer.add_line
                    added.append(add(data, **{"name": Path(path).stem, **kwargs}))
                    continue

        reader = plugin
        if reader is None:
            readers = _npe2.get_readers(path)
            reader = get_preferred_reader(path)
            if reader not in readers:
                if not readers:
                    raise NoAvailableReaderError(f"No plugin found capable of reading {path}.", group)
                if len(readers) > 1:
                    raise MultipleReaderError(f"Multiple reader plugins support {path}.", list(readers), group)
                reader = next(iter(readers))
        try:
            items, reader = read_data_with_plugins(group, plugin=reader, stack=len(group) > 1 or bool(stack))
        except Exception as error:
            raise ReaderPluginError(f"Tried opening {path} with {reader}, but failed.", reader, group, error) from error

        group_layers = []
        for item in items or []:
            if isinstance(item, Layer):
                item._set_source(Source(path=path, reader_plugin=reader))
                group_layers.append(item)
                continue
            data, *options = item
            meta = options[0].copy() if options else {}
            meta.update(kwargs)
            meta.setdefault("name", Path(parsed.path).stem)
            kind = layer_type or (options[1] if len(options) == 2 else None)
            with layer_source(path=path, reader_plugin=reader):
                group_layers.append(Layer.create(data, meta, kind))
        viewer.layers.extend(group_layers)
        added.extend(group_layers)
    return added
