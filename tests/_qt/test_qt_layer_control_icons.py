"""Regression tests for stylesheet-backed layer control icons."""

from __future__ import annotations

from collections.abc import Iterable

from napari.layers import Shapes
from napari._qt.layer_controls.qt_shapes_controls import QtShapesControls
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QPushButton

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
