"""Qt controls for Rectangles."""

import numpy as np
from napari.settings import get_settings
from pytestqt.qtbot import QtBot

from napari_plot._qt.layer_controls.qt_layer_controls_container import layer_to_controls
from napari_plot._qt.layer_controls.qt_rectangles_controls import QtRectanglesControls
from napari_plot.layers import Rectangles


def test_rectangles_controls_sync_independently(qtbot: QtBot) -> None:
    layer = Rectangles([[1, 2]], 3, 4, text=["Peak"])
    controls = layer_to_controls[Rectangles](layer)
    assert isinstance(controls, QtRectanglesControls)
    qtbot.addWidget(controls)

    controls.markers_checkbox.setChecked(True)
    controls.outlines_checkbox.setChecked(False)
    assert layer.show_markers
    assert not layer.show_rectangles
    assert layer.show_text
    controls.text_checkbox.setChecked(False)
    assert not layer.show_text
    assert layer.show_markers

    controls.width_slider.setValue(3.5)
    assert layer.outline_width == 3.5
    layer.outline_width = 4.5
    layer.show_markers = False
    layer.show_rectangles = True
    layer.show_text = True
    assert controls.width_slider.value() == 4.5
    assert not controls.markers_checkbox.isChecked()
    assert controls.outlines_checkbox.isChecked()
    assert controls.text_checkbox.isChecked()


def test_rectangles_mode_buttons_use_distinct_icons(qtbot: QtBot) -> None:
    """Add uses the shared add icon and edit does not duplicate the pan/zoom icon."""
    controls = QtRectanglesControls(Rectangles([[1, 2]], 3, 4))
    qtbot.addWidget(controls)
    assert controls.add_button.icon_text == "add"
    assert controls.edit_button.icon_text == "select_points"


def test_rectangles_marker_and_font_style_controls(qtbot: QtBot) -> None:
    layer = Rectangles([[1, 2], [3, 4]], 3, 4, marker_size=[5, 8], marker_symbol=["disc", "diamond"])
    controls = QtRectanglesControls(layer)
    qtbot.addWidget(controls)

    # per-marker sizes show the first value; unset font size shows the application default
    assert controls.marker_size_slider.value() == 5
    assert controls.marker_symbol_combobox.currentIndex() == -1
    assert controls.text_size_slider.value() == get_settings().appearance.font_size
    np.testing.assert_array_equal(layer.marker_size, [5, 8])
    np.testing.assert_array_equal(layer.marker_symbol, ["disc", "diamond"])
    assert layer.text_size is None

    controls.marker_size_slider.setValue(9)
    controls.marker_symbol_combobox.setCurrentIndex(controls.marker_symbol_combobox.findData("triangle_up"))
    controls.text_size_slider.setValue(14)
    assert layer.marker_size == 9
    assert layer.marker_symbol == "triangle_up"
    assert layer.text_size == 14

    layer.marker_size = 7
    layer.marker_symbol = "square"
    layer.text_size = 12
    assert controls.marker_size_slider.value() == 7
    assert controls.marker_symbol_combobox.currentData() == "square"
    assert controls.text_size_slider.value() == 12

    layer.marker_symbol = ["disc", "square"]
    assert controls.marker_symbol_combobox.currentIndex() == -1


def test_rectangles_integer_sliders_receive_ints(qtbot: QtBot, monkeypatch) -> None:
    """PyQt rejects float values for integer sliders, so sizes must be cast before syncing."""
    from superqt import QLabeledSlider

    values = []
    original = QLabeledSlider.setValue
    # QLabeledDoubleSlider subclasses QLabeledSlider, so only record the integer sliders
    monkeypatch.setattr(
        QLabeledSlider,
        "setValue",
        lambda self, value: (type(self) is QLabeledSlider and values.append(value), original(self, value)),
    )
    controls = QtRectanglesControls(Rectangles([[1, 2], [3, 4]], 3, 4, marker_size=[5.5, 8], text_size=12.5))
    qtbot.addWidget(controls)
    assert values
    assert all(type(value) is int for value in values)
