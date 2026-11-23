"""Export entry point tests without an OpenGL context."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import numpy as np
import pytest
from qtpy.QtCore import QMimeData, QPointF, Qt, QUrl
from qtpy.QtGui import QDropEvent, QImage
from qtpy.QtSvg import QSvgGenerator
from qtpy.QtWidgets import QMainWindow, QWidget
from vispy.scene import Node, Widget
from vispy.scene.visuals import Axis, Image, Line, Markers, Mesh, Text

from napari_plot._qt import qt_main_window, qt_viewer
from napari_plot._qt.qt_main_window import Window
from napari_plot._qt.qt_viewer import QtViewer
from napari_plot._qt.qt_welcome import QtWidgetOverlay
from napari_plot.components.camera import ExtentMode
from napari_plot.components.viewer_model import ViewerModel

if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.monkeypatch import MonkeyPatch
    from pytestqt.qtbot import QtBot


class _CanvasViewer:
    """Provide QtViewer's screenshot and file handling dependencies."""

    _capture_view = QtViewer._capture_view
    _screenshot = QtViewer._screenshot
    resize_canvas = QtViewer.resize_canvas
    screenshot = QtViewer.screenshot
    _screenshot_dialog = QtViewer._screenshot_dialog
    _open_from_list_of_urls_data = QtViewer._open_from_list_of_urls_data
    _qt_open = QtViewer._qt_open

    def __init__(self) -> None:
        self.viewer = ViewerModel()
        self.canvas = SimpleNamespace(
            size=(80, 100),
            _cells=[],
            native=SimpleNamespace(devicePixelRatioF=lambda: 1),
            screenshot=self._capture,
        )
        self.captured_rects = []

    def _capture(self) -> QImage:
        self.captured_rects.append(self.viewer.camera.rect)
        height, width = self.canvas.size
        image = QImage(width, height, QImage.Format.Format_RGBA8888)
        image.fill(Qt.GlobalColor.red)
        return image

    def clipboard(self) -> None:
        """Record the canvas capture for the menu test."""
        self._screenshot(flash=False)


class _Window:
    """Exercise Window's menu and exports with a test canvas."""

    _screenshot = Window._screenshot
    _screenshot_dialog = Window._screenshot_dialog
    screenshot = Window.screenshot
    export_figure = Window.export_figure
    export_vector = Window.export_vector
    export_rois = Window.export_rois
    clipboard = Window.clipboard
    _export_figure_dialog = Window._export_figure_dialog
    _export_csv_dialog = Window._export_csv_dialog
    _save_session_dialog = Window._save_session_dialog
    _open_session_dialog = Window._open_session_dialog

    def __init__(self, widget: QMainWindow) -> None:
        self._qt_window = widget
        self.main_menu = widget.menuBar()
        self._qt_viewer = _CanvasViewer()


def test_screenshot_menu_actions(tmp_path: Path, qtbot: QtBot, monkeypatch: MonkeyPatch) -> None:
    widget = QMainWindow()
    qtbot.addWidget(widget)
    widget.close_window = widget.close
    window = _Window(widget)
    clipboard = SimpleNamespace(setImage=lambda image: saved_images.append(image))
    saved_images = []
    import qtpy.QtGui

    monkeypatch.setattr(qtpy.QtGui.QGuiApplication, "clipboard", lambda: clipboard)
    monkeypatch.setattr("napari._qt.utils.add_flash_animation", lambda _: None)

    class _SaveDialog:
        def __init__(self, save, _parent):
            self.save = save

        def exec(self) -> None:
            self.save(str(tmp_path / f"screenshot-{self.save.__self__.__class__.__name__}.png"))

    monkeypatch.setattr(qt_viewer, "ScreenshotDialog", _SaveDialog)
    monkeypatch.setattr(qt_main_window, "ScreenshotDialog", _SaveDialog)
    Window._add_file_menu(window)
    for action in window.file_menu.actions()[:4]:
        action.trigger()

    assert (tmp_path / "screenshot-_CanvasViewer.png").exists()
    assert (tmp_path / "screenshot-_Window.png").exists()
    assert len(window._qt_viewer.captured_rects) == 2
    assert len(saved_images) == 1


def test_figure_csv_and_session_menu_actions(tmp_path: Path, qtbot: QtBot, monkeypatch: MonkeyPatch) -> None:
    widget = QMainWindow()
    qtbot.addWidget(widget)
    widget.close_window = widget.close
    window = _Window(widget)
    viewer = window._qt_viewer.viewer
    viewer.add_line([[1, 2], [3, 4]], name="samples")
    monkeypatch.setattr("napari._qt.utils.add_flash_animation", lambda _: None)
    filenames = {
        "Export Figure": tmp_path / "figure.png",
        "Export Layer Data": tmp_path / "data.csv",
        "Save Plot Session": tmp_path / "figure.napari-plot",
    }
    monkeypatch.setattr(qt_main_window.hp, "get_save_filename", lambda _parent, title, **_: str(filenames[title]))
    monkeypatch.setattr(qt_main_window.hp, "get_filename", lambda *_, **__: str(filenames["Save Plot Session"]))
    Window._add_file_menu(window)
    actions = {action.text(): action for action in window.file_menu.actions()}
    actions["Export Figure..."].trigger()
    actions["Export Active Layer as CSV..."].trigger()
    actions["Save Plot Session..."].trigger()

    assert all(filename.exists() for filename in filenames.values())
    viewer.layers.clear()
    actions["Open Plot Session..."].trigger()
    assert [layer.name for layer in viewer.layers] == ["samples"]


def test_figure_and_roi_exports_restore_view(tmp_path: Path, qtbot: QtBot, monkeypatch: MonkeyPatch) -> None:
    widget = QMainWindow()
    qtbot.addWidget(widget)
    window = _Window(widget)
    viewer = window._qt_viewer.viewer
    viewer.add_line([[-5, -2], [5, 2]])
    viewer.camera.set_x_range(-1, 1)
    viewer.camera.extent_mode = ExtentMode.RESTRICTED
    old_rect, old_extent = viewer.camera.rect, viewer.camera.extent

    full = window.export_figure(tmp_path / "figure.png", 2, flash=False)
    assert full.shape == (160, 200, 4)
    exported_rect = window._qt_viewer.captured_rects[-1]
    assert exported_rect[0] <= -5
    assert exported_rect[1] >= 5
    roi = np.asarray([[-1, -3], [-1, 3], [1, 3], [1, -3]])
    (cropped,) = window.export_rois([roi], tmp_path / "rois")
    assert cropped.shape == (80, 100, 4)
    assert (tmp_path / "rois" / "roi_0.png").exists()
    assert window._qt_viewer.captured_rects[-1] == (-3, 3, -1, 1)

    def fail_capture() -> None:
        raise RuntimeError("capture failed")

    monkeypatch.setattr(window._qt_viewer.canvas, "screenshot", fail_capture)
    with pytest.raises(RuntimeError, match="capture failed"):
        window.export_rois([roi], scale=2)
    assert window._qt_viewer.canvas.size == (80, 100)
    assert viewer.camera.rect == old_rect
    assert viewer.camera.extent == old_extent
    assert viewer.camera.extent_mode is ExtentMode.RESTRICTED


def test_drop_local_plot_csv(tmp_path: Path, qtbot: QtBot) -> None:
    viewer = _CanvasViewer()
    widget = QtWidgetOverlay(None, QWidget())
    qtbot.addWidget(widget)
    widget.sig_dropped.connect(viewer._open_from_list_of_urls_data)
    path = tmp_path / "two columns.csv"
    path.write_text("x,y\n1,2\n3,4\n")
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(path))])
    event = QDropEvent(
        QPointF(), Qt.DropAction.CopyAction, mime_data, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
    )

    widget._overlay.dropEvent(event)

    assert event.isAccepted()
    assert viewer.viewer.layers[0].name == path.stem
    np.testing.assert_array_equal(viewer.viewer.layers[0].data, [[1, 2], [3, 4]])


def test_figure_writes_requested_dpi(tmp_path: Path, qtbot: QtBot) -> None:
    path = tmp_path / "figure.png"
    widget = QMainWindow()
    qtbot.addWidget(widget)
    window = _Window(widget)

    image = window.export_figure(path, dpi=192, flash=False)

    assert image.shape == (160, 200, 4)
    assert QImage(str(path)).dotsPerMeterX() == round(192 / 0.0254)


def test_save_vector_formats(tmp_path: Path, qtbot: QtBot) -> None:
    root = Widget(size=(10, 10))
    view = root.add_grid().add_view(row=0, col=0)
    node = Node(parent=view)
    trace = Line(pos=np.asarray([[20, 6], [30, 16], [40, 6]]), color="red", parent=node)
    Markers(pos=np.asarray([[15, 20]]), parent=node)
    Mesh(vertices=np.asarray([[3, 8], [5, 6], [7, 9]]), faces=np.asarray([[0, 1, 2]]), parent=node)
    Text("vector curve", pos=(50, 25), parent=node)
    Image(np.ones((3, 4)), clim=(0, 2), parent=node)
    axis = Axis(pos=np.array([[10, 50], [90, 50]]), domain=(0, 2), axis_label="wavelength", parent=root)
    axis.transforms.dpi = 96
    widget = QMainWindow()
    qtbot.addWidget(widget)
    window = _Window(widget)
    canvas = window._qt_viewer.canvas
    canvas._scene_canvas = SimpleNamespace(central_widget=root, bgcolor=(1, 1, 1, 1), size=(100, 80))
    layer = window._qt_viewer.viewer.add_line([[0, 0], [1, 2]], dashes=(3, 2))
    canvas.layer_to_visual = {layer: SimpleNamespace(node=trace)}
    canvas._cells = [
        SimpleNamespace(
            view=view, data_scene=node, camera=SimpleNamespace(rect=(0, 1, 0, 1), restore_cell_rect=lambda _: None)
        )
    ]
    path = tmp_path / "plot.svg"

    window.export_vector(path)
    window.export_vector(tmp_path / "plot.pdf", dpi=300)

    assert root.size == (10, 10)
    svg = path.read_text()
    assert "<polyline" in svg
    assert "stroke-dasharray" in svg
    assert "vector curve" in svg
    assert "wavelength" in svg
    assert any(tag in svg for tag in ("<circle", "<ellipse"))
    assert "<image" in svg
    if hasattr(QSvgGenerator, "SvgVersion"):
        assert "<clipPath" in svg
    assert (tmp_path / "plot.pdf").read_bytes().startswith(b"%PDF-")
