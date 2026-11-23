"""Session and layer data export tests."""

from __future__ import annotations

import csv
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pytest

from napari_plot.components.viewer_model import ViewerModel


def test_session_round_trip(tmp_path: Path) -> None:
    viewer = ViewerModel()
    viewer.theme = "light"
    viewer.axis.x_label = "Retention time"
    viewer.canvas.grid.enabled = True
    viewer.canvas.grid.sharex = False
    viewer.canvas.grid.cell(1, 0).xlim = (3, 9)
    line = viewer.add_line([[4, 1], [8, 2]], name="trace", color="orange", metadata={"trace": 3})
    image = viewer.add_image(np.arange(6, dtype=np.uint16).reshape(3, 2), name="image")
    viewer.camera.rect = (3, 10, 0, 12)
    viewer.set_colorbar_from_layer(image, "intensity", cell=(1, 0), position="bottom")
    viewer.add_text_overlay("annotation", name="fit")
    viewer.layers.selection.active = line

    path = tmp_path / "plot.napari-plot"
    viewer.save_session(path)
    restored = ViewerModel()
    restored.add_line([[0, 0], [1, 1]])
    new_line, new_image = restored.open(path)

    np.testing.assert_array_equal(new_line.data, line.data)
    np.testing.assert_array_equal(new_line.color, line.color)
    assert new_line.metadata == line.metadata
    np.testing.assert_array_equal(new_image.data, image.data)
    assert new_image.data.dtype == np.uint16
    assert restored.layers.selection.active is new_line
    assert restored.theme == "light"
    assert restored.axis.x_label == "Retention time"
    assert restored.camera.rect == (3, 10, 0, 12)
    assert not restored.canvas.grid.sharex
    assert restored.canvas.grid.cell(1, 0).xlim == (3, 9)
    assert restored._overlays["annotation:fit"].text == "annotation"
    assert restored.colorbar_for_cell(1, 0).orientation == "horizontal"
    new_image.contrast_limits = (1, 4)
    assert restored.colorbar_for_cell(1, 0).contrast_limits == (1, 4)


def test_invalid_session_preserves_existing_layers(tmp_path: Path) -> None:
    viewer = ViewerModel()
    layer = viewer.add_line([[1, 3], [2, 4]])
    path = tmp_path / "invalid.napari-plot"
    with ZipFile(path, "w") as archive:
        archive.writestr("session.json", '{"version": 999}')

    with pytest.raises(ValueError, match="version"):
        viewer.load_session(path)

    assert list(viewer.layers) == [layer]


def test_open_with_native_reader(tmp_path: Path) -> None:
    data = np.arange(15, dtype=np.float64).reshape(3, 5)
    path = tmp_path / "image.npy"
    np.save(path, data)

    (layer,) = ViewerModel().open(path)

    np.testing.assert_array_equal(layer.data, data)
    assert Path(layer.source.path).resolve() == path.resolve()


def test_csv_layer_data(tmp_path: Path) -> None:
    viewer = ViewerModel()
    line = viewer.add_line([[1, 3], [2, 4]], name="trace")
    path = tmp_path / "trace.csv"
    viewer.export_csv("trace", path)

    assert path.read_text().splitlines() == ["x,y", "1,3", "2,4"]
    (restored,) = ViewerModel().open(path)
    np.testing.assert_array_equal(restored.data, line.data)

    text = viewer.add_text([[1, 2]], text="caption, with comma")
    viewer.export_csv(text, path)
    with path.open(newline="") as stream:
        assert list(csv.reader(stream)) == [["x", "y", "text"], ["1.0", "2.0", "caption, with comma"]]
