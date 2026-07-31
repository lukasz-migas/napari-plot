"""Regression tests for stylesheet-backed layer control icons."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pytest
from napari._qt.layer_controls.qt_image_controls import QtImageControls
from napari._qt.layer_controls.qt_points_controls import QtPointsControls
from napari._qt.layer_controls.qt_shapes_controls import QtShapesControls
from napari.layers import Image, Points, Shapes
from qtextra.config import THEMES
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QPushButton

from napari_plot._qt.layer_controls.qt_layer_controls_container import QtLayerControlsContainer
from napari_plot._qt.layer_controls.qt_scatter_controls import QtScatterControls
from napari_plot.components.viewer_model import ViewerModel
from napari_plot.layers import Scatter
from napari_plot.resources import get_stylesheet


def _get_opaque_colors(button: QPushButton) -> set[tuple[int, int, int, int]]:
    """Return all opaque colors rendered for a button."""
    image = button.grab().toImage()
    colors: set[tuple[int, int, int, int]] = set()

    for x_coord in range(image.width()):
        for y_coord in range(image.height()):
            color = image.pixelColor(x_coord, y_coord)
            if color.alpha() > 0:
                colors.add(_to_rgba_tuple(color))

    return colors


def _to_rgba_tuple(color: QColor) -> tuple[int, int, int, int]:
    """Convert a Qt color to a comparable RGBA tuple."""
    return color.red(), color.green(), color.blue(), color.alpha()


def _make_builtin_controls(layer_name: str) -> QtImageControls | QtPointsControls | QtShapesControls:
    """Create representative controls for a built-in napari layer."""
    if layer_name == "image":
        controls = QtImageControls(Image(np.ones((2, 2))))
    elif layer_name == "points":
        controls = QtPointsControls(Points(np.zeros((1, 2))))
    elif layer_name == "shapes":
        controls = QtShapesControls(Shapes(ndim=2))
    else:
        raise ValueError(f"Unknown layer name: {layer_name}")
    controls.setProperty("napari_builtin", True)
    return controls


def test_layer_controls_container_marks_builtin_controls(qtbot) -> None:
    """The container marks only controls implemented by napari as built-in."""
    viewer = ViewerModel()
    container = QtLayerControlsContainer(viewer)
    qtbot.addWidget(container)
    image = Image(np.ones((2, 2)))
    scatter = Scatter(np.zeros((1, 2)))

    viewer.layers.extend([image, scatter])

    assert container.widgets[image].property("napari_builtin") is True
    assert container.widgets[scatter].property("napari_builtin") is False


def test_shapes_action_icons_render_with_napari_plot_stylesheet(qtbot, qapp) -> None:
    """Ensure built-in shapes action buttons still render icons."""
    previous_stylesheet = qapp.styleSheet()
    qapp.setStyleSheet(get_stylesheet("dark"))

    try:
        layer = Shapes(ndim=2)
        controls = QtShapesControls(layer)
        qtbot.addWidget(controls)
        controls.show()
        qapp.processEvents()

        buttons: Iterable[QPushButton] = (
            controls.select_button,
            controls.move_front_button,
            controls.move_back_button,
            controls.delete_button,
        )

        for button in buttons:
            assert len(_get_opaque_colors(button)) > 1
    finally:
        qapp.setStyleSheet(previous_stylesheet)


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("layer_name", ["image", "points", "shapes"])
def test_builtin_mode_button_checked_state(qtbot, qapp, theme: str, layer_name: str) -> None:
    """Checked built-in mode buttons retain their icon and highlighted background."""
    previous_stylesheet = qapp.styleSheet()
    qapp.setStyleSheet(get_stylesheet(theme))

    try:
        controls = _make_builtin_controls(layer_name)
        qtbot.addWidget(controls)
        controls.show()
        qapp.processEvents()

        button = controls.panzoom_button
        image = button.grab().toImage()
        expected_background = QColor(THEMES.get_theme(theme).current.as_hex())

        assert button.isChecked()
        assert image.pixelColor(5, 5) == expected_background
        assert image.pixelColor(image.width() // 2, image.height() // 2) != expected_background
    finally:
        qapp.setStyleSheet(previous_stylesheet)


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("layer_name", ["image", "shapes"])
def test_builtin_layer_slider_grooves_are_visible(qtbot, qapp, theme: str, layer_name: str) -> None:
    """Built-in opacity and gamma sliders use the higher-contrast groove color."""
    previous_stylesheet = qapp.styleSheet()
    qapp.setStyleSheet(get_stylesheet(theme))

    try:
        controls = _make_builtin_controls(layer_name)
        qtbot.addWidget(controls)
        sliders = [controls._opacity_blending_controls.opacity_slider]
        if layer_name == "image":
            sliders.append(controls._gamma_slider_control.gamma_slider)

        controls.show()
        sliders[0].setValue(0.5)
        qapp.processEvents()
        expected_groove = QColor(THEMES.get_theme(theme).primary.as_hex())

        for slider in sliders:
            image = slider._slider.grab().toImage()
            assert image.pixelColor(image.width() - 5, image.height() // 2) == expected_groove
    finally:
        qapp.setStyleSheet(previous_stylesheet)


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_custom_layer_slider_keeps_qtextra_style(qtbot, qapp, theme: str) -> None:
    """Built-in compatibility rules do not restyle custom plot controls."""
    previous_stylesheet = qapp.styleSheet()
    qapp.setStyleSheet(get_stylesheet(theme))

    try:
        controls = QtScatterControls(Scatter(np.zeros((1, 2)), opacity=0.5))
        controls.setProperty("napari_builtin", False)
        qtbot.addWidget(controls)
        controls.show()
        qapp.processEvents()

        slider = controls.opacity_slider._slider
        image = slider.grab().toImage()
        expected_handle = QColor(THEMES.get_theme(theme).highlight.as_hex())

        assert image.pixelColor(image.width() // 2, image.height() // 2) == expected_handle
    finally:
        qapp.setStyleSheet(previous_stylesheet)
