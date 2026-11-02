"""Regression tests for visible layer-control slider tracks."""

from __future__ import annotations

import numpy as np
import pytest
from napari._qt.layer_controls.dynamic.widgets import QtOpacityBlendingControls
from pytestqt.qtbot import QtBot
from qtextra.config import THEMES
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QApplication

from napari_plot._qt.layer_controls.qt_layer_controls_container import QtLayerControlsContainer
from napari_plot._qt.layer_controls.qt_scatter_controls import QtScatterControls
from napari_plot.components.viewer_model import ViewerModel
from napari_plot.layers import Scatter
from napari_plot.resources import get_stylesheet


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("relative", [True, False])
def test_scatter_border_width_groove_is_visible(qtbot: QtBot, qapp: QApplication, theme: str, relative: bool) -> None:
    """Relative and absolute border widths retain a contrasting slider track."""
    previous_stylesheet = qapp.styleSheet()
    qapp.setStyleSheet(get_stylesheet(theme))

    try:
        layer = Scatter([[0, 0]], border_width=0.1, border_width_is_relative=relative)
        controls = QtScatterControls(layer)
        qtbot.addWidget(controls)
        controls.show()
        qapp.processEvents()

        image = controls.border_width_slider._slider.grab().toImage()
        expected_groove = QColor(THEMES.get_theme(theme).primary.as_hex())

        assert image.pixelColor(image.width() - 5, image.height() // 2) == expected_groove
    finally:
        qapp.setStyleSheet(previous_stylesheet)


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("layer_types", [("scatter", "scatter"), ("scatter", "image"), ("image", "image")])
def test_shared_opacity_groove_is_visible(
    qtbot: QtBot, qapp: QApplication, theme: str, layer_types: tuple[str, str]
) -> None:
    """Custom, mixed, and built-in selections retain a visible opacity track."""
    previous_stylesheet = qapp.styleSheet()
    qapp.setStyleSheet(get_stylesheet(theme))

    try:
        viewer = ViewerModel()
        container = QtLayerControlsContainer(viewer)
        qtbot.addWidget(container)
        for layer_type in layer_types:
            if layer_type == "scatter":
                viewer.add_scatter([[0, 0]], opacity=0.5)
            else:
                viewer.add_image(np.zeros((2, 2)), opacity=0.5)
        viewer.layers.selection.update(viewer.layers)
        container.show()
        qapp.processEvents()

        panel = container.panel
        assert panel is not None
        assert container.currentWidget() is panel
        controls = panel.findChild(QtOpacityBlendingControls)
        assert controls is not None
        image = controls.opacity_slider._slider.grab().toImage()
        expected_groove = QColor(THEMES.get_theme(theme).primary.as_hex())

        assert image.pixelColor(image.width() - 5, image.height() // 2) == expected_groove
    finally:
        qapp.setStyleSheet(previous_stylesheet)
