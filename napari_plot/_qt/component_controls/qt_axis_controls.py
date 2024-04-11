"""X/Y-axis controls"""

from typing import TYPE_CHECKING

from weakref import ref
from napari._qt.utils import set_widgets_enabled_with_opacity, qt_signals_blocked
from napari._qt.widgets.qt_color_swatch import QColorSwatch
from napari.utils.events import disconnect_events
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout, QWidget

import napari_plot._qt.helpers as hp
from napari_plot._qt.qt_dialog import QtFramelessPopup

if TYPE_CHECKING:
    from napari_plot.components.viewer_model import ViewerModel


class QtAxisWidget(QWidget):
    """Popup to control camera model."""

    def __init__(self, viewer: "ViewerModel", parent):
        super().__init__(parent=parent)
        self.ref_viewer = ref(viewer)
        viewer.axis.events.visible.connect(self._on_visible_change)
        viewer.axis.events.x_label.connect(self._on_label_change)
        viewer.axis.events.y_label.connect(self._on_label_change)
        viewer.axis.events.label_color.connect(self._on_label_color_change)
        viewer.axis.events.label_size.connect(self._on_tick_label_size_change)
        viewer.axis.events.tick_color.connect(self._on_tick_color_change)
        viewer.axis.events.tick_size.connect(self._on_tick_font_size_change)
        viewer.axis.events.x_label_margin.connect(self._on_label_margin_change)
        viewer.axis.events.y_label_margin.connect(self._on_label_margin_change)
        viewer.axis.events.x_tick_margin.connect(self._on_tick_margin_change)
        viewer.axis.events.y_tick_margin.connect(self._on_tick_margin_change)
        viewer.axis.events.x_max_size.connect(self._on_max_size_change)
        viewer.axis.events.y_max_size.connect(self._on_max_size_change)

        self.visible_checkbox = hp.make_checkbox(self, "", val=viewer.axis.visible, tooltip="Show/hide x/y-axes")
        self.visible_checkbox.stateChanged.connect(self.on_change_visible)

        self.x_axis_edit = hp.make_line_edit(self, viewer.axis.x_label, placeholder="X-axis label...")
        self.x_axis_edit.textChanged.connect(self.on_change_label)

        self.x_label_margin_spin = hp.make_slider_with_text(
            self, min_value=10, max_value=120, step_size=5, value=viewer.axis.x_label_margin
        )
        self.x_label_margin_spin.valueChanged.connect(self.on_change_label_margin)

        self.y_axis_edit = hp.make_line_edit(self, viewer.axis.y_label, placeholder="Y-axis label...")
        self.y_axis_edit.textChanged.connect(self.on_change_label)

        self.y_label_margin_spin = hp.make_slider_with_text(
            self, min_value=10, max_value=120, step_size=5, value=viewer.axis.y_label_margin
        )
        self.y_label_margin_spin.valueChanged.connect(self.on_change_label_margin)

        self.label_color_swatch = QColorSwatch(
            initial_color=viewer.axis.label_color,
            tooltip="Click to set label color",
        )
        self.label_color_swatch.color_changed.connect(self.on_change_label_color)

        self.label_font_size = hp.make_double_slider(
            self, min_value=4, max_value=16, step_size=1, value=viewer.axis.label_size
        )
        self.label_font_size.valueChanged.connect(self.on_change_label_font_size)

        self.tick_color_swatch = QColorSwatch(
            initial_color=viewer.axis.tick_color,
            tooltip="Click to set tick color",
        )
        self.tick_color_swatch.color_changed.connect(self.on_change_tick_color)

        self.x_max_size_spin = hp.make_slider_with_text(
            self,
            min_value=50,
            max_value=150,
            step_size=5,
            value=viewer.axis.x_max_size,
            tooltip="Maximum height (x-axis) of the axes visual.",
        )
        self.x_max_size_spin.valueChanged.connect(self.on_change_max_size)

        self.y_max_size_spin = hp.make_slider_with_text(
            self,
            min_value=50,
            max_value=150,
            step_size=5,
            value=viewer.axis.y_max_size,
            tooltip="Maximum height width (y-axis) of the axes visual.",
        )
        self.y_max_size_spin.valueChanged.connect(self.on_change_max_size)

        self.tick_font_size = hp.make_double_slider(
            self, min_value=4, max_value=16, step_size=1, value=viewer.axis.tick_size
        )
        self.tick_font_size.valueChanged.connect(self.on_change_tick_font_size)

        self.x_tick_margin_spin = hp.make_slider_with_text(
            self,
            min_value=5,
            max_value=100,
            step_size=5,
            value=viewer.axis.x_tick_margin,
            tooltip="Distance between ticks and tick labels.",
        )
        self.x_tick_margin_spin.valueChanged.connect(self.on_change_tick_margin)

        self.y_tick_margin_spin = hp.make_slider_with_text(
            self,
            min_value=5,
            max_value=100,
            step_size=5,
            value=viewer.axis.y_tick_margin,
            tooltip="Distance between ticks and tick labels.",
        )
        self.y_tick_margin_spin.valueChanged.connect(self.on_change_tick_margin)

        layout = QFormLayout(self)
        layout.addRow(hp.make_label(self, "Visible"), self.visible_checkbox)
        layout.addRow(hp.make_label(self, "X-axis label"), self.x_axis_edit)
        layout.addRow(hp.make_label(self, "X-axis label margin"), self.x_label_margin_spin)
        layout.addRow(hp.make_label(self, "X-axis tick margin"), self.x_tick_margin_spin)
        layout.addRow(hp.make_h_line(self))
        layout.addRow(hp.make_label(self, "Y-axis label"), self.y_axis_edit)
        layout.addRow(hp.make_label(self, "Y-axis label margin"), self.y_label_margin_spin)
        layout.addRow(hp.make_label(self, "Y-axis tick margin"), self.y_tick_margin_spin)
        layout.addRow(hp.make_h_line(self))
        layout.addRow(hp.make_label(self, "Label color"), self.label_color_swatch)
        layout.addRow(hp.make_label(self, "Label font size"), self.label_font_size)
        layout.addRow(hp.make_label(self, "Tick color"), self.tick_color_swatch)
        layout.addRow(hp.make_label(self, "Tick font size"), self.tick_font_size)
        layout.addRow(hp.make_label(self, "Max height"), self.x_max_size_spin)
        layout.addRow(hp.make_label(self, "Max width"), self.y_max_size_spin)
        layout.setSpacing(2)

        set_widgets_enabled_with_opacity(self, [self.x_max_size_spin, self.y_max_size_spin], False)

    def on_change_visible(self):
        """Change visibility of the axes."""
        self.ref_viewer().axis.visible = self.visible_checkbox.isChecked()

    def _on_visible_change(self, _event=None):
        """Update visibility checkbox."""
        with self.ref_viewer().axis.events.visible.blocker():
            self.visible_checkbox.setChecked(self.ref_viewer().axis.visible)

    def on_change_label(self):
        """Change visibility of the x/y-axis."""
        self.ref_viewer().axis.x_label = self.x_axis_edit.text()
        self.ref_viewer().axis.y_label = self.y_axis_edit.text()

    def _on_label_change(self, _event=None):
        """Update x/y-axis checkbox."""
        with self.ref_viewer().axis.events.x_label.blocker():
            self.x_axis_edit.setText(self.ref_viewer().axis.x_label)
        with self.ref_viewer().axis.events.y_label.blocker():
            self.y_axis_edit.setText(self.ref_viewer().axis.y_label)

    def on_change_label_margin(self):
        """Update margin of the x/y-axis label."""
        self.ref_viewer().axis.x_label_margin = self.x_label_margin_spin.value()
        self.ref_viewer().axis.y_label_margin = self.y_label_margin_spin.value()

    def _on_label_margin_change(self, _event=None):
        """Update x/y-axis margin spinboxes."""
        with self.ref_viewer().axis.events.x_label_margin.blocker():
            self.x_label_margin_spin.setValue(self.ref_viewer().axis.x_label_margin)
        with self.ref_viewer().axis.events.y_label_margin.blocker():
            self.y_label_margin_spin.setValue(self.ref_viewer().axis.y_label_margin)

    def on_change_tick_margin(self):
        """Update tick margin."""
        self.ref_viewer().axis.x_tick_margin = self.x_tick_margin_spin.value()
        self.ref_viewer().axis.y_tick_margin = self.y_tick_margin_spin.value()

    def _on_tick_margin_change(self, _event=None):
        """Update tick margin spinboxes."""
        with self.ref_viewer().axis.events.x_tick_margin.blocker():
            self.x_tick_margin_spin.setValue(self.ref_viewer().axis.x_tick_margin)
        with self.ref_viewer().axis.events.y_tick_margin.blocker():
            self.y_tick_margin_spin.setValue(self.ref_viewer().axis.y_tick_margin)

    def on_change_max_size(self):
        """Change maximum width/height of the axes."""
        self.ref_viewer().axis.x_max_size = self.x_max_size_spin.value()
        self.ref_viewer().axis.y_max_size = self.y_max_size_spin.value()

    def _on_max_size_change(self, _event=None):
        """Update width/height spinboxes."""
        with self.ref_viewer().axis.events.x_max_size.blocker():
            self.x_max_size_spin.setValue(self.ref_viewer().axis.x_max_size)
        with self.ref_viewer().axis.events.y_max_size.blocker():
            self.y_max_size_spin.setValue(self.ref_viewer().axis.y_max_size)

    def on_change_tick_font_size(self):
        """Change font size of the tick."""
        self.ref_viewer().axis.tick_size = self.tick_font_size.value()

    def _on_tick_font_size_change(self, _event=None):
        """Update font size spinbox."""
        with self.ref_viewer().axis.events.tick_size.blocker():
            self.tick_font_size.setValue(self.ref_viewer().axis.tick_size)

    def on_change_tick_color(self, color: str):
        """Update tick color from color picker user input."""
        self.ref_viewer().axis.tick_color = color

    def _on_tick_color_change(self, _event=None):
        """Update color swatch of the tick color."""
        with qt_signals_blocked(self.tick_color_swatch):
            self.tick_color_swatch.setColor(self.ref_viewer().axis.tick_color)

    def on_change_label_font_size(self):
        """Change font size of the label."""
        self.ref_viewer().axis.label_size = self.label_font_size.value()

    def _on_tick_label_size_change(self, _event=None):
        """Update label font size spinbox."""
        with self.ref_viewer().axis.events.label_size.blocker():
            self.label_font_size.setValue(self.ref_viewer().axis.label_size)

    def on_change_label_color(self, color: str):
        """Update label color swatch of the tick color."""
        self.ref_viewer().axis.label_color = color

    def _on_label_color_change(self, _event=None):
        """Update color swatch of the label color."""
        with qt_signals_blocked(self.label_color_swatch):
            self.label_color_swatch.setColor(self.ref_viewer().axis.label_color)


class QtAxisControls(QtFramelessPopup):
    """Popup to control x/y-axis visual"""

    def __init__(self, viewer: "ViewerModel", parent=None):
        self.ref_viewer = ref(viewer)

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("axis")
        self.setMouseTracking(True)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel"""
        widget = QtAxisWidget(self.ref_viewer(), self)
        layout = QFormLayout()
        layout.addRow(self._make_move_handle("Axis controls"))
        layout.addRow(widget)
        return layout

    def close(self):
        """Disconnect events when widget is closing."""
        disconnect_events(self.ref_viewer().axis.events, self)
        super().close()
