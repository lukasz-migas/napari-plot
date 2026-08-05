"""Tests for the napari-embedded plotting widget."""

from __future__ import annotations

import pytest
from napari.utils.theme import _themes, get_theme
from qtextra.assets import MISSING, QTA_MAPPING
from qtextra.config import THEMES
from qtextra.widgets.qt_button_icon import QtImagePushButton
from qtpy.QtGui import QColor

from napari_plot._plot_widget import NapariPlotWidget, _synchronize_qtextra_theme

TOOLBAR_ICONS = (
    "erase",
    "zoom_out",
    "screenshot",
    "zoom",
    "axes",
    "text",
    "grid",
    "list",
    "tool",
    "layers",
)


def _assert_icon_uses_active_theme(button: QtImagePushButton) -> None:
    """Assert an opaque toolbar glyph uses qtextra's active icon color."""
    image = button.icon().pixmap(button.iconSize()).toImage()
    expected = QColor(THEMES.get_hex_color("icon")).rgb()
    colors = {
        image.pixelColor(x, y).rgb()
        for x in range(image.width())
        for y in range(image.height())
        if image.pixelColor(x, y).alpha()
    }
    assert expected in colors


@pytest.mark.parametrize(("initial_theme", "updated_theme"), [("dark", "light"), ("light", "dark")])
def test_embedded_widget_loads_assets_and_tracks_theme(
    make_napari_viewer,
    qtbot,
    initial_theme: str,
    updated_theme: str,
) -> None:
    """Embedded widgets receive complete assets and follow the host theme."""
    _synchronize_qtextra_theme(updated_theme)
    napari_icon_colors = {name: theme.icon for name, theme in _themes.items()}
    viewer = make_napari_viewer(strict_qt=False)
    viewer.theme = initial_theme
    widget = NapariPlotWidget(viewer)
    qtbot.addWidget(widget)

    assert viewer.theme == initial_theme
    assert THEMES.theme == initial_theme
    assert widget.viewer_plot.theme == initial_theme
    assert widget.styleSheet()
    assert "NapariPlotControls" in widget.styleSheet()
    assert all(QTA_MAPPING.get(name) not in (None, QTA_MAPPING[MISSING]) for name in TOOLBAR_ICONS)
    toolbar_button = widget.qt_viewer.viewerToolbar.tools_zoomout_btn
    _assert_icon_uses_active_theme(toolbar_button)

    initial_stylesheet = widget.styleSheet()
    initial_icon_key = toolbar_button.icon().cacheKey()
    viewer.theme = updated_theme

    assert viewer.theme == updated_theme
    assert THEMES.theme == updated_theme
    assert widget.viewer_plot.theme == updated_theme
    assert widget.styleSheet() != initial_stylesheet
    assert toolbar_button.icon().cacheKey() != initial_icon_key
    _assert_icon_uses_active_theme(toolbar_button)
    assert {name: theme.icon for name, theme in _themes.items()} == napari_icon_colors


def test_embedded_widget_maps_system_theme_to_qtextra(make_napari_viewer, qtbot) -> None:
    """System napari themes use the corresponding qtextra palette type."""
    viewer = make_napari_viewer(strict_qt=False)
    widget = NapariPlotWidget(viewer)
    qtbot.addWidget(widget)

    viewer.theme = "system"

    assert viewer.theme == "system"
    assert widget.viewer_plot.theme == "system"
    assert THEMES.theme == get_theme("system").type
    _assert_icon_uses_active_theme(widget.qt_viewer.viewerToolbar.tools_zoomout_btn)


def test_floating_layer_controls_are_compact(make_napari_viewer, qtbot) -> None:
    """The floating layer panel has no outer padding or layout spacing."""
    viewer = make_napari_viewer(strict_qt=False)
    widget = NapariPlotWidget(viewer)
    qtbot.addWidget(widget)
    widget.qt_viewer.on_open_controls_dialog()
    dialog = widget.qt_viewer._layers_controls_dialog

    assert dialog is not None
    margins = dialog.layout().contentsMargins()
    assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (0, 0, 0, 0)
    assert dialog.layout().spacing() == 2
