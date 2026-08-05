"""Tests for the napari-embedded plotting widget."""

from __future__ import annotations

import pytest
from qtextra.assets import MISSING, QTA_MAPPING

from napari_plot._plot_widget import NapariPlotWidget

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


@pytest.mark.parametrize(("initial_theme", "updated_theme"), [("dark", "light"), ("light", "dark")])
def test_embedded_widget_loads_assets_and_tracks_theme(
    make_napari_viewer,
    qtbot,
    initial_theme: str,
    updated_theme: str,
) -> None:
    """Embedded widgets receive complete assets and follow the host theme."""
    viewer = make_napari_viewer(strict_qt=False)
    viewer.theme = initial_theme
    widget = NapariPlotWidget(viewer)
    qtbot.addWidget(widget)

    assert widget.viewer_plot.theme == initial_theme
    assert widget.styleSheet()
    assert "NapariPlotControls" in widget.styleSheet()
    assert all(QTA_MAPPING.get(name) not in (None, QTA_MAPPING[MISSING]) for name in TOOLBAR_ICONS)

    initial_stylesheet = widget.styleSheet()
    viewer.theme = updated_theme

    assert widget.viewer_plot.theme == updated_theme
    assert widget.styleSheet() != initial_stylesheet


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
