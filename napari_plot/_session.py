"""Read and write portable plot sessions."""

from __future__ import annotations

import json
from contextlib import suppress
from datetime import date, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Any
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
from napari.components.overlays import TextOverlay
from napari.layers import Layer
from pydantic import BaseModel

if TYPE_CHECKING:
    from napari_plot.components.viewer_model import ViewerModel

SESSION_SUFFIX = ".napari-plot"


def save_session(viewer: ViewerModel, path: str | Path) -> None:
    """Write a versioned archive with plot settings, layer state and array data."""
    path = Path(path).expanduser()
    saved_layers = []
    for layer in viewer.layers:
        data, metadata, layer_type = layer.as_layer_data_tuple()
        # Multiscale image data and lazy arrays expose a sequence or array protocol.
        if getattr(layer, "multiscale", False):
            data = [np.asarray(level) for level in data]
        elif hasattr(data, "__array__"):
            data = np.asarray(data)
        metadata = dict(metadata)
        if metadata.get("units") is not None:
            metadata["units"] = tuple(str(unit) for unit in metadata["units"])
        saved_layers.append((data, metadata, layer_type))

    state = {
        "version": 1,
        "title": viewer.title,
        "theme": viewer.theme,
        "axis": viewer.axis.model_dump(
            exclude={key for key in type(viewer.axis).model_fields if key.endswith("formatter")}
        ),
        "camera": viewer.camera.model_dump(),
        "grid": viewer.canvas.grid.model_dump(),
        "dims": viewer.dims.model_dump(),
        "canvas": viewer.canvas.model_dump(include={"background_color_override", "overlay_tiling"}),
        "colorbar": viewer.colorbar.model_dump(),
        "cell_colorbars": [(cell, colorbar.model_dump()) for cell, colorbar in viewer._cell_colorbars.items()],
        "colorbar_sources": [(cell, viewer.layers.index(layer)) for cell, layer in viewer._colorbar_sources.items()],
        "legend": viewer.legend.model_dump(),
        "grid_lines": viewer._overlays["grid_lines"].model_dump(),
        "text": viewer.text_overlay.model_dump(),
        "annotations": {name: viewer._overlays[name].model_dump() for name in viewer._text_overlay_names},
        "explicit_axis_labels": sorted(viewer._explicit_axis_labels),
        "layers": saved_layers,
        "selection": [viewer.layers.index(layer) for layer in viewer.layers.selection],
    }
    state.update(autoscale=viewer.autoscale, margins=viewer.margins)

    with NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with ZipFile(temporary_path, "w", compression=ZIP_DEFLATED) as archive:
            array_index = 0

            def encode(value: Any) -> Any:
                nonlocal array_index
                if isinstance(value, np.ndarray):
                    if value.dtype.hasobject:
                        return value.tolist()
                    entry = f"arrays/{array_index}.npy"
                    array_index += 1
                    with archive.open(entry, "w", force_zip64=True) as array_file:
                        np.save(array_file, value, allow_pickle=False)
                    return {"$array": entry}
                if isinstance(value, np.generic):
                    return value.item()
                if isinstance(value, (date, datetime)):
                    return value.isoformat()
                if isinstance(value, Path):
                    return str(value)
                if isinstance(value, BaseModel):
                    return value.model_dump()
                if type(value).__module__.split(".", 1)[0] == "pandas" and type(value).__name__ == "DataFrame":
                    return value.to_dict(orient="list")
                raise TypeError(f"Session values of type {type(value).__name__} cannot be saved.")

            archive.writestr("session.json", json.dumps(state, default=encode))
        temporary_path.replace(path)
    finally:
        with suppress(FileNotFoundError):
            temporary_path.unlink()


def load_session(viewer: ViewerModel, path: str | Path) -> list[Layer]:
    """Replace the viewer with the layers and settings in a saved session."""
    with ZipFile(Path(path).expanduser()) as archive:

        def decode(value: dict[str, Any]) -> Any:
            if value.keys() == {"$array"}:
                with archive.open(value["$array"]) as array_file:
                    return np.load(array_file, allow_pickle=False)
            return value

        state = json.loads(archive.read("session.json"), object_hook=decode)
    if state.get("version") != 1:
        raise ValueError("Unsupported plot session version.")

    title = state["title"]
    theme = viewer._valid_theme(state["theme"])
    if not isinstance(title, str):
        raise TypeError("Invalid plot session title.")
    dims = type(viewer.dims).model_validate(state["dims"])
    canvas = type(viewer.canvas).model_validate(state["canvas"])
    layers = [Layer.create(*layer_state) for layer_state in state["layers"]]
    selection = [layers[index] for index in state["selection"]]
    axis = type(viewer.axis).model_validate(state["axis"])
    grid = type(viewer.canvas.grid).model_validate(state["grid"])
    camera_state = state["camera"]
    camera_state["axis_mode"] = tuple(camera_state["axis_mode"])
    camera = type(viewer.camera).model_validate(camera_state)
    colorbar = type(viewer.colorbar).model_validate(state["colorbar"])
    cell_colorbars = {tuple(cell): type(colorbar).model_validate(options) for cell, options in state["cell_colorbars"]}
    sources = {None if cell is None else tuple(cell): layers[index] for cell, index in state["colorbar_sources"]}
    legend = type(viewer.legend).model_validate(state["legend"])
    text = TextOverlay.model_validate(state["text"])
    annotations = {name: TextOverlay.model_validate(options) for name, options in state["annotations"].items()}
    grid_lines = type(viewer._overlays["grid_lines"]).model_validate(state["grid_lines"])

    viewer.reset_plot()
    for cell in tuple(viewer._cell_colorbars):
        viewer.clear_colorbar(cell=cell)
    viewer._cell_colorbars.clear()
    viewer.events.colorbars_change()
    viewer.theme = theme
    viewer.title = title
    viewer.canvas.background_color_override = canvas.background_color_override
    viewer.canvas.overlay_tiling.update(canvas.overlay_tiling)
    viewer.axis.update(axis)
    viewer._explicit_axis_labels = set(state["explicit_axis_labels"])
    viewer.canvas.grid.update(grid)
    viewer.layers.extend(layers)
    viewer.dims.update(dims)
    viewer.text_overlay.update(text)
    viewer._overlays["grid_lines"].update(grid_lines)
    viewer._overlays.update(annotations)
    viewer._text_overlay_names = list(annotations)
    viewer.legend.update(legend)
    viewer.refresh_legend_from_source()
    viewer.colorbar.update(colorbar)
    for cell, model in cell_colorbars.items():
        viewer.colorbar_for_cell(*cell).update(model)
    for cell, layer in sources.items():
        model = colorbar if cell is None else cell_colorbars[cell]
        viewer.set_colorbar_from_layer(layer, model.label, cell=cell).visible = model.visible
    for field in ("autoscale", "margins"):
        if field in state:
            setattr(viewer, field, state[field])
    viewer.layers.selection.clear()
    viewer.layers.selection.update(selection)
    viewer.camera.update(camera)
    return layers
