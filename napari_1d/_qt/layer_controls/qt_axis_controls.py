"""X/Y-axis controls"""
from typing import TYPE_CHECKING

from napari._qt.utils import disable_with_opacity, qt_signals_blocked
from napari._qt.widgets.qt_color_swatch import QColorSwatch
from napari.utils.events import disconnect_events
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout

from ..helpers import make_checkbox, make_label, make_line_edit, make_slider, make_h_line
from ..qt_dialog import QtFramelessPopup

if TYPE_CHECKING:
    from ...components.viewer_model import ViewerModel


class QtAxisControls(QtFramelessPopup):
    """Popup to control x/y-axis visual"""

    def __init__(self, viewer: "ViewerModel", parent=None):
        self.viewer = viewer

        super().__init__(parent=parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.viewer.axis.events.visible.connect(self._on_visible_change)
        self.viewer.axis.events.x_label.connect(self._on_label_change)
        self.viewer.axis.events.y_label.connect(self._on_label_change)
        self.viewer.axis.events.label_color.connect(self._on_label_color_change)
        self.viewer.axis.events.label_size.connect(self._on_tick_label_size_change)
        self.viewer.axis.events.tick_color.connect(self._on_tick_color_change)
        self.viewer.axis.events.tick_size.connect(self._on_tick_font_size_change)
        self.viewer.axis.events.x_label_margin.connect(self._on_label_margin_change)
        self.viewer.axis.events.y_label_margin.connect(self._on_label_margin_change)
        self.viewer.axis.events.x_tick_margin.connect(self._on_tick_margin_change)
        self.viewer.axis.events.y_tick_margin.connect(self._on_tick_margin_change)
        self.viewer.axis.events.x_max_size.connect(self._on_max_size_change)
        self.viewer.axis.events.y_max_size.connect(self._on_max_size_change)

        self.setObjectName("axis")
        self.setMouseTracking(True)

        disable_with_opacity(self, ["x_max_size_spin", "y_max_size_spin"], True)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel"""
        self.visible_checkbox = make_checkbox(self, "", val=self.viewer.axis.visible, tooltip="Show/hide x/y-axes")
        self.visible_checkbox.stateChanged.connect(self.on_change_visible)  # noqa

        self.x_axis_edit = make_line_edit(self, self.viewer.axis.x_label, placeholder="X-axis label...")
        self.x_axis_edit.textChanged.connect(self.on_change_label)  # noqa

        self.x_label_margin_spin = make_slider(
            self, min_value=10, max_value=120, step_size=5, value=self.viewer.axis.x_label_margin
        )
        self.x_label_margin_spin.valueChanged.connect(self.on_change_label_margin)  # noqa

        self.y_axis_edit = make_line_edit(self, self.viewer.axis.y_label, placeholder="Y-axis label...")
        self.y_axis_edit.textChanged.connect(self.on_change_label)  # noqa

        self.y_label_margin_spin = make_slider(
            self, min_value=10, max_value=120, step_size=5, value=self.viewer.axis.y_label_margin
        )
        self.y_label_margin_spin.valueChanged.connect(self.on_change_label_margin)  # noqa

        self.label_color_swatch = QColorSwatch(
            initial_color=self.viewer.axis.label_color,
            tooltip="Click to set label color",
        )
        self.label_color_swatch.color_changed.connect(self.on_change_label_color)  # noqa

        self.label_font_size = make_slider(
            self, min_value=4, max_value=16, step_size=1, value=self.viewer.axis.label_size
        )
        self.label_font_size.valueChanged.connect(self.on_change_label_font_size)  # noqa

        self.tick_color_swatch = QColorSwatch(
            initial_color=self.viewer.axis.tick_color,
            tooltip="Click to set tick color",
        )
        self.tick_color_swatch.color_changed.connect(self.on_change_tick_color)  # noqa

        self.x_max_size_spin = make_slider(
            self,
            min_value=50,
            max_value=150,
            step_size=5,
            value=self.viewer.axis.x_max_size,
            tooltip="Maximum height (x-axis) of the axes visual.",
        )
        self.x_max_size_spin.valueChanged.connect(self.on_change_max_size)  # noqa

        self.y_max_size_spin = make_slider(
            self,
            min_value=50,
            max_value=150,
            step_size=5,
            value=self.viewer.axis.y_max_size,
            tooltip="Maximum height width (y-axis) of the axes visual.",
        )
        self.y_max_size_spin.valueChanged.connect(self.on_change_max_size)  # noqa

        self.tick_font_size = make_slider(
            self, min_value=4, max_value=16, step_size=1, value=self.viewer.axis.tick_size
        )
        self.tick_font_size.valueChanged.connect(self.on_change_tick_font_size)  # noqa

        self.x_tick_margin_spin = make_slider(
            self,
            min_value=5,
            max_value=100,
            step_size=5,
            value=self.viewer.axis.x_tick_margin,
            tooltip="Distance between ticks and tick labels.",
        )
        self.x_tick_margin_spin.valueChanged.connect(self.on_change_tick_margin)  # noqa

        self.y_tick_margin_spin = make_slider(
            self,
            min_value=5,
            max_value=100,
            step_size=5,
            value=self.viewer.axis.y_tick_margin,
            tooltip="Distance between ticks and tick labels.",
        )
        self.y_tick_margin_spin.valueChanged.connect(self.on_change_tick_margin)  # noqa

        layout = QFormLayout(self)
        layout.addRow(self._make_move_handle())  # noqa
        layout.addRow(make_label(self, "Visible"), self.visible_checkbox)
        layout.addRow(make_label(self, "X-axis label"), self.x_axis_edit)
        layout.addRow(make_label(self, "Y-axis label"), self.y_axis_edit)
        layout.addRow(make_label(self, "X-axis label margin"), self.x_label_margin_spin)
        layout.addRow(make_label(self, "X-axis tick margin"), self.x_tick_margin_spin)
        layout.addRow(make_h_line(self))  # noqa
        layout.addRow(make_label(self, "Label color"), self.label_color_swatch)
        layout.addRow(make_label(self, "Label font size"), self.label_font_size)
        layout.addRow(make_label(self, "Tick color"), self.tick_color_swatch)
        layout.addRow(make_label(self, "Tick font size"), self.tick_font_size)
        layout.addRow(make_label(self, "Y-axis label margin"), self.y_label_margin_spin)
        layout.addRow(make_label(self, "Y-axis tick margin"), self.y_tick_margin_spin)
        layout.addRow(make_h_line(self))  # noqa
        layout.addRow(make_label(self, "Max height"), self.x_max_size_spin)
        layout.addRow(make_label(self, "Max width"), self.y_max_size_spin)
        layout.setSpacing(2)
        return layout

    def on_change_visible(self):
        """Change visibility of the axes."""
        self.viewer.axis.visible = self.visible_checkbox.isChecked()

    def _on_visible_change(self, _event=None):
        """Update visibility checkbox."""
        with self.viewer.axis.events.visible.blocker():
            self.visible_checkbox.setChecked(self.viewer.axis.visible)

    def on_change_label(self):
        """Change visibility of the x/y-axis."""
        self.viewer.axis.x_label = self.x_axis_edit.text()
        self.viewer.axis.y_label = self.y_axis_edit.text()

    def _on_label_change(self, _event=None):
        """Update x/y-axis checkbox."""
        with self.viewer.axis.events.x_label.blocker():
            self.x_axis_edit.setText(self.viewer.axis.x_label)
        with self.viewer.axis.events.y_label.blocker():
            self.y_axis_edit.setText(self.viewer.axis.y_label)

    def on_change_label_margin(self):
        """Update margin of the x/y-axis label."""
        self.viewer.axis.x_label_margin = self.x_label_margin_spin.value()
        self.viewer.axis.y_label_margin = self.y_label_margin_spin.value()

    def _on_label_margin_change(self, _event=None):
        """Update x/y-axis margin spinboxes."""
        with self.viewer.axis.events.x_label_margin.blocker():
            self.x_label_margin_spin.setValue(self.viewer.axis.x_label_margin)
        with self.viewer.axis.events.y_label_margin.blocker():
            self.y_label_margin_spin.setValue(self.viewer.axis.y_label_margin)

    def on_change_tick_margin(self):
        """Update tick margin."""
        self.viewer.axis.x_tick_margin = self.x_tick_margin_spin.value()
        self.viewer.axis.y_tick_margin = self.y_tick_margin_spin.value()

    def _on_tick_margin_change(self, _event=None):
        """Update tick margin spinboxes."""
        with self.viewer.axis.events.x_tick_margin.blocker():
            self.x_tick_margin_spin.setValue(self.viewer.axis.x_tick_margin)
        with self.viewer.axis.events.y_tick_margin.blocker():
            self.y_tick_margin_spin.setValue(self.viewer.axis.y_tick_margin)

    def on_change_max_size(self):
        """Change maximum width/height of the axes."""
        self.viewer.axis.x_max_size = self.x_max_size_spin.value()
        self.viewer.axis.y_max_size = self.y_max_size_spin.value()

    def _on_max_size_change(self, _event=None):
        """Update width/height spinboxes."""
        with self.viewer.axis.events.x_max_size.blocker():
            self.x_max_size_spin.setValue(self.viewer.axis.x_max_size)
        with self.viewer.axis.events.y_max_size.blocker():
            self.y_max_size_spin.setValue(self.viewer.axis.y_max_size)

    def on_change_tick_font_size(self):
        """Change font size of the tick."""
        self.viewer.axis.tick_size = self.tick_font_size.value()

    def _on_tick_font_size_change(self, _event=None):
        """Update font size spinbox."""
        with self.viewer.axis.events.tick_size.blocker():
            self.tick_font_size.setValue(self.viewer.axis.tick_size)

    def on_change_tick_color(self, color: str):
        """Update tick color from color picker user input."""
        self.viewer.axis.tick_color = color

    def _on_tick_color_change(self, _event=None):
        """Update color swatch of the tick color."""
        with qt_signals_blocked(self.tick_color_swatch):
            self.tick_color_swatch.setColor(self.viewer.axis.tick_color)

    def on_change_label_font_size(self):
        """Change font size of the label."""
        self.viewer.axis.label_size = self.label_font_size.value()

    def _on_tick_label_size_change(self, _event=None):
        """Update label font size spinbox."""
        with self.viewer.axis.events.label_size.blocker():
            self.label_font_size.setValue(self.viewer.axis.label_size)

    def on_change_label_color(self, color: str):
        """Update label color swatch of the tick color."""
        self.viewer.axis.label_color = color

    def _on_label_color_change(self, _event=None):
        """Update color swatch of the label color."""
        with qt_signals_blocked(self.label_color_swatch):
            self.label_color_swatch.setColor(self.viewer.axis.label_color)

    def close(self):
        """Disconnect events when widget is closing."""
        disconnect_events(self.viewer.axis.events, self)
        super().close()
