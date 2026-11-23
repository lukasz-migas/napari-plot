"""Tests for the model, controls, and VisPy legend overlay."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from napari._vispy.utils.qt_font import FontInfo
from napari._vispy.utils.visual import overlay_to_visual
from napari.components._viewer_constants import CanvasPosition
from vispy.scene import ViewBox, Widget

from napari_plot._qt.component_controls.qt_legend_controls import QtLegendControls
from napari_plot._vispy.overlays import register_vispy_overlays
from napari_plot._vispy.overlays.legend import VispyLegendOverlay, legend_layout_size
from napari_plot.components.legend import LegendEntry, LegendOverlay, legend_entries_from_points
from napari_plot.components.viewer_model import ViewerModel


def test_legend_models_validate_entries_and_style() -> None:
    """Legend entries normalize marker aliases, colors, and placement."""
    entry = LegendEntry(label="cell", marker="o", color="red")
    overlay = LegendOverlay(entries=[entry], position="bottom_left")

    assert entry.marker == "disc"
    np.testing.assert_allclose(entry.color, [1, 0, 0, 1])
    assert overlay.position is CanvasPosition.BOTTOM_LEFT

    with pytest.raises(ValueError, match="single color"):
        LegendEntry(label="bad", color=["red", "blue"])
    with pytest.raises(ValueError, match="positive"):
        LegendOverlay(font_size=0)
    with pytest.raises(ValueError, match="non-negative"):
        LegendOverlay(border_width=-1)


def test_default_legend_tracks_visible_plot_layers() -> None:
    """The hidden default overlay stays synchronized with layer state and style."""
    viewer = ViewerModel()
    assert isinstance(viewer.legend, LegendOverlay)
    assert not viewer.legend.visible
    assert viewer.legend.sync_with_source

    line = viewer.add_line([[0, 0], [1, 1]], name="signal", color="red")
    bar = viewer.add_bar([2, 3], name="bars", fill_color="blue")
    viewer.add_image(np.ones((2, 2)), name="image")

    assert [entry.label for entry in viewer.legend.entries] == ["signal", "bars"]
    assert [entry.marker for entry in viewer.legend.entries] == ["hbar", "square"]
    np.testing.assert_allclose(viewer.legend.entries[1].color, [0, 0, 1, 1])

    line.name = "renamed"
    line.color = "green"
    assert viewer.legend.entries[0].label == "renamed"
    np.testing.assert_allclose(viewer.legend.entries[0].color, [0, 0.50196078, 0, 1])

    line.visible = False
    assert [entry.label for entry in viewer.legend.entries] == ["bars"]
    line.visible = True
    viewer.layers.move(viewer.layers.index(bar), viewer.layers.index(line))
    assert [entry.label for entry in viewer.legend.entries] == ["bars", "renamed"]


def test_manual_legend_and_auto_sync_controls() -> None:
    """Explicit entries pause source sync until it is enabled again."""
    viewer = ViewerModel()
    viewer.add_line([[0, 0], [1, 1]], name="line")

    overlay = viewer.set_legend([{"label": "Manual", "color": "yellow"}])
    assert not overlay.sync_with_source
    assert [entry.label for entry in overlay.entries] == ["Manual"]

    viewer.set_legend_auto_sync(True)
    assert [entry.label for entry in overlay.entries] == ["line"]
    viewer.clear_legend()
    assert not overlay.entries
    assert not overlay.visible


def test_points_legend_can_group_and_sync_styles() -> None:
    """Categorized Points data can generate style-aware legend rows."""
    viewer = ViewerModel()
    points = viewer.add_points(
        [[0, 0], [1, 1], [2, 2]],
        name="objects",
        properties={"label": ["cell", "cell", "nucleus"]},
        face_color=["red", "blue", "green"],
        symbol=["disc", "square", "diamond"],
    )

    entries = legend_entries_from_points(points)
    assert [entry.label for entry in entries] == ["cell", "cell", "nucleus"]

    overlay = viewer.set_legend_from_points(points, sync=True)
    points.face_color = ["yellow", "blue", "green"]
    np.testing.assert_allclose(overlay.entries[0].color, [1, 1, 0, 1])

    points.name = "renamed objects"
    assert overlay.source_layer == "renamed objects"
    points.face_color = ["purple", "blue", "green"]
    np.testing.assert_allclose(overlay.entries[0].color, [0.50196078, 0, 0.50196078, 1])


def test_vispy_legend_registration_and_geometry() -> None:
    """The overlay maps to its VisPy visual and reacts to model changes."""
    register_vispy_overlays()
    assert overlay_to_visual[LegendOverlay] is VispyLegendOverlay

    viewer = ViewerModel()
    overlay = viewer.set_legend([{"label": "Cell", "marker": "disc", "color": "red"}])
    visual = VispyLegendOverlay(viewer=viewer, overlay=overlay, font_info=FontInfo())

    assert legend_layout_size(overlay) == (visual.x_size, visual.y_size)
    assert visual.x_size > 0
    assert visual.y_size > 0
    overlay.set_entries(None)
    assert visual.x_size == 0
    assert visual.y_size == 0
    visual.close()


def test_vispy_legend_markers_follow_parent_clipper() -> None:
    """Markers added after parenting to a ViewBox can be detached from its clipper."""
    viewer = ViewerModel()
    overlay = viewer.set_legend([{"label": "a"}])
    visual = VispyLegendOverlay(viewer=viewer, overlay=overlay, font_info=FontInfo())
    view_box = ViewBox()
    visual.node.parent = view_box

    overlay.set_entries([{"label": label, "marker": "square", "color": "red"} for label in "abc"])
    assert len(visual._markers) == 3
    overlay.set_entries([{"label": "a", "marker": "square", "color": "red"}])
    assert len(visual._markers) == 1
    assert all(view_box._clipper in marker._filters for marker in visual._markers)

    visual.node.parent = None
    assert all(view_box._clipper not in marker._filters for marker in visual._markers)
    visual.close()


def test_viewer_with_explicit_legend_closes_cleanly(make_napari_plot_viewer) -> None:
    """Closing a viewer with explicit legend entries tears down the overlay without errors."""
    viewer = make_napari_plot_viewer(show=True)
    viewer.set_legend([{"label": "a", "marker": "square", "color": "red"}])
    viewer.close()


def test_vispy_legend_click_toggles_layer() -> None:
    """Clicking an automatic legend row toggles its source layer."""
    viewer = ViewerModel()
    line = viewer.add_line([[0, 0], [1, 1]], name="signal")
    overlay = viewer.set_legend_from_layers(sync=True)
    parent = Widget(size=(300, 200), pos=(0, 0))
    visual = VispyLegendOverlay(viewer=viewer, overlay=overlay, font_info=FontInfo())
    visual.node.parent = parent
    visual.node.transform.translate = [10, 10, 0, 0]
    event = SimpleNamespace(pos=(20, 20), button=1, handled=False)

    visual._on_mouse_press(event)

    assert not line.visible
    assert event.handled
    visual.close()


def test_legend_controls_update_overlay(qtbot) -> None:
    """The popup edits visibility, placement, synchronization, and style."""
    viewer = ViewerModel()
    viewer.add_line([[0, 0], [1, 1]], name="line")
    controls = QtLegendControls(viewer)
    qtbot.addWidget(controls)

    controls.visible_checkbox.setChecked(True)
    controls.on_change_visible()
    controls.position_combobox.setCurrentIndex(controls.position_combobox.findData(CanvasPosition.BOTTOM_LEFT))
    controls.on_change_position()
    controls.font_size_spinbox.setValue(18)
    controls.on_change_font_size()
    controls.marker_size_spinbox.setValue(16)
    controls.on_change_marker_size()
    controls.on_change_text_color(np.asarray([0.0, 1.0, 0.0, 1.0]))

    assert viewer.legend.visible
    assert viewer.legend.position is CanvasPosition.BOTTOM_LEFT
    assert viewer.legend.font_size == 18
    assert viewer.legend.marker_size == 16
    np.testing.assert_allclose(viewer.legend.text_color, [0, 1, 0, 1])


def test_legend_controls_use_current_visibility(qtbot) -> None:
    """Opening controls reflects toolbar-driven legend state."""
    viewer = ViewerModel()
    viewer.set_legend_visible(True)
    controls = QtLegendControls(viewer)
    qtbot.addWidget(controls)

    assert controls.visible_checkbox.isChecked()
    assert controls.auto_sync_checkbox.isChecked()

    viewer.set_legend_visible(False)
    assert not controls.visible_checkbox.isChecked()
    controls.visible_checkbox.click()
    assert viewer.legend.visible


def test_legend_controls_disconnect_when_qt_closes_popup(qtbot) -> None:
    """Reopening controls after a Qt-driven close does not call into the deleted popup."""
    from qtpy.QtCore import QCoreApplication, QEvent
    from qtpy.QtWidgets import QWidget

    viewer = ViewerModel()
    controls = QtLegendControls(viewer)
    controls.show()
    # popups closed by clicking outside go through closeEvent, not the Python ``close`` override
    QWidget.close(controls)
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    second = QtLegendControls(viewer)
    qtbot.addWidget(second)
    second.row_spacing_spinbox.setValue(7)
    second.on_change_row_spacing()
    assert viewer.legend.row_spacing == 7


def test_theme_colors_and_outside_legend(make_napari_plot_viewer) -> None:
    viewer = make_napari_plot_viewer()
    viewer.rectangle((1, 2), 3, 4, color="red", name="regions")
    viewer.plot([1, 2], name="profile")
    viewer.set_legend_from_layers(title="Samples", ncols=2, outside=True)
    canvas = viewer.window._qt_viewer.canvas
    visual = canvas._overlay_to_visual[viewer.legend][0]
    canvas._update_overlay_canvas_positions()
    assert [entry.label for entry in viewer.legend.entries] == ["regions", "profile"]
    assert visual.node.parent is visual._outside_widget
    assert list(visual._text.text) == ["Samples", "regions", "profile"]
    assert visual._text.pos[1, 1] == visual._text.pos[2, 1]
    assert visual._text.pos[1, 0] < visual._text.pos[2, 0]

    dark_text = canvas.x_axis.node.axis.text_color.rgba[0].copy()
    dark_background = visual._background.color.rgba.copy()
    viewer.theme = "light"
    assert canvas.x_axis.node.axis.text_color.rgba[0, :3].mean() < dark_text[:3].mean()
    assert visual._background.color.rgba[:3].mean() > dark_background[:3].mean()
    viewer.axis.label_color = "red"
    viewer.theme = "dark"
    np.testing.assert_allclose(canvas.x_axis.node.axis.text_color.rgba[0], [1, 0, 0, 1])

    viewer.legend.outside = False
    assert visual.node.parent is canvas.view
