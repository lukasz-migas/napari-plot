"""Camera controls"""

import typing as ty
from weakref import ref

import qtextra.helpers as hp
from napari.utils.events import disconnect_events
from qtextra.widgets.qt_dialog import QtFramelessPopup
from qtpy.QtCore import Qt
from qtpy.QtGui import QDoubleValidator
from qtpy.QtWidgets import QFormLayout, QWidget

from napari_plot.components.camera import EXTENT_MODE_TRANSLATIONS, CameraMode

if ty.TYPE_CHECKING:
    from napari_plot.components.viewer_model import ViewerModel


class QtCameraWidget(QWidget):
    """Popup to control camera model."""

    def __init__(self, viewer: "ViewerModel", parent):
        super().__init__(parent=parent)
        self.ref_viewer = ref(viewer)
        viewer.camera.events.mouse_pan.connect(self._on_interactive_changed)
        viewer.camera.events.mouse_zoom.connect(self._on_interactive_changed)
        viewer.camera.events.aspect.connect(self._on_aspect_changed)
        viewer.camera.events.extent.connect(self._on_extent_changed)
        viewer.camera.events.rect.connect(self._on_rect_changed)
        viewer.camera.events.x_range.connect(self._on_x_range_changed)
        viewer.camera.events.y_range.connect(self._on_y_range_changed)
        viewer.camera.events.extent_mode.connect(self._on_extent_mode_changed)
        viewer.camera.events.axis_mode.connect(self._on_axis_mode_changed)

        self.mouse_pan_checkbox = hp.make_checkbox(self, "", tooltip="Enable/disable mouse pan")
        self.mouse_pan_checkbox.setChecked(viewer.camera.mouse_pan)
        self.mouse_pan_checkbox.stateChanged.connect(self.on_change_interactive)
        self.mouse_zoom_checkbox = hp.make_checkbox(self, "", tooltip="Enable/disable mouse pan")
        self.mouse_zoom_checkbox.setChecked(viewer.camera.mouse_zoom)
        self.mouse_zoom_checkbox.stateChanged.connect(self.on_change_interactive)

        self.extent_mode = hp.make_combobox(
            self,
            tooltip="Control whether the axes should be zoom-able outside of the plotted data.",
        )
        hp.set_combobox_data(
            self.extent_mode,
            EXTENT_MODE_TRANSLATIONS,
            self.ref_viewer().camera.extent_mode,
        )
        self.extent_mode.currentIndexChanged.connect(self.on_change_extent_mode)

        self.aspect = hp.make_double_spin_box(
            self,
            tooltip="Upper x-axis range",
            minimum=-1e10,
            maximum=1e10,
            n_decimals=3,
        )
        self.aspect.valueChanged.connect(self.on_change_aspect)

        # extents
        self.extent_x_min = hp.make_double_spin_box(
            self, tooltip="Lower x-axis range", minimum=-1e10, maximum=1e10, n_decimals=6, func=self.on_change_extent
        )
        self.extent_x_max = hp.make_double_spin_box(
            self, tooltip="Upper x-axis range", minimum=-1e10, maximum=1e10, n_decimals=6, func=self.on_change_extent
        )

        self.extent_y_min = hp.make_double_spin_box(
            self, tooltip="Lower y-axis range", minimum=-1e10, maximum=1e10, n_decimals=6, func=self.on_change_extent
        )
        self.extent_y_max = hp.make_double_spin_box(
            self, tooltip="Upper y-axis range", minimum=-1e10, maximum=1e10, n_decimals=6, func=self.on_change_extent
        )

        # ranges
        self.x_min = hp.make_double_spin_box(
            self, tooltip="Lower x-axis range", minimum=-1e10, maximum=1e10, n_decimals=6, func=self.on_change_rect
        )
        self.x_max = hp.make_double_spin_box(
            self, tooltip="Upper x-axis range", minimum=-1e10, maximum=1e10, n_decimals=6, func=self.on_change_rect
        )

        self.y_min = hp.make_double_spin_box(
            self, tooltip="Lower y-axis range", minimum=-1e10, maximum=1e10, n_decimals=6, func=self.on_change_rect
        )
        self.y_max = hp.make_double_spin_box(
            self, tooltip="Upper y-axis range", minimum=-1e10, maximum=1e10, n_decimals=6, func=self.on_change_rect
        )

        validator = QDoubleValidator(parent=self)
        self.x_range_min = hp.make_line_edit(
            self, tooltip="Lower x-axis range", validator=validator, func=self.on_change_x_range
        )
        self.x_range_max = hp.make_line_edit(
            self, tooltip="Upper x-axis range", validator=validator, func=self.on_change_x_range
        )
        self.x_range_reset = hp.make_btn(self, "Reset x-range", func=self.on_reset_x_range)

        self.y_range_min = hp.make_line_edit(
            self, tooltip="Lower x-axis range", validator=validator, func=self.on_change_y_range
        )
        self.y_range_max = hp.make_line_edit(
            self, tooltip="Upper x-axis range", validator=validator, func=self.on_change_y_range
        )
        self.y_range_reset = hp.make_btn(self, "Reset y-range", func=self.on_reset_y_range)

        self.axis_mode_all = hp.make_btn(self, "Unlock all", func=self.on_change_axis_mode)
        self.axis_mode_bottom = hp.make_checkbox(
            self,
            tooltip="Lock to bottom. Whenever you zoom-in or out, the bottom x-axis value will be at the minimum.",
            func=self.on_change_axis_mode,
        )
        self.axis_mode_top = hp.make_checkbox(
            self,
            tooltip="Lock to top. Whenever you zoom-in or out, the top x-axis value will be at the maximum.",
            func=self.on_change_axis_mode,
        )
        self.axis_mode_left = hp.make_checkbox(
            self,
            tooltip="Lock to left. Whenever you zoom-in or out, the left y-axis value will be at the minimum.",
            func=self.on_change_axis_mode,
        )
        self.axis_mode_right = hp.make_checkbox(
            self,
            tooltip="Lock to right. Whenever you zoom-in or out, the right y-axis value will be at the maximum.",
            func=self.on_change_axis_mode,
        )

        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.addRow(hp.make_label(self, "Interactive zoom"), self.mouse_zoom_checkbox)
        layout.addRow(hp.make_label(self, "Interactive pan"), self.mouse_pan_checkbox)
        layout.addRow(hp.make_label(self, "Restriction mode"), self.extent_mode)
        layout.addRow(hp.make_label(self, "Aspect ratio"), self.aspect)
        layout.addRow(hp.make_h_line_with_text("Extents", bold=True))
        layout.addRow(hp.make_label(self, "x (min)"), self.extent_x_min)
        layout.addRow(hp.make_label(self, "x (max)"), self.extent_x_max)
        layout.addRow(hp.make_label(self, "y (min)"), self.extent_y_min)
        layout.addRow(hp.make_label(self, "y (max)"), self.extent_y_max)
        layout.addRow(hp.make_h_line_with_text("Current limits", bold=True))
        layout.addRow(hp.make_label(self, "x (min)"), self.x_min)
        layout.addRow(hp.make_label(self, "x (max)"), self.x_max)
        layout.addRow(hp.make_label(self, "y (min)"), self.y_min)
        layout.addRow(hp.make_label(self, "y (max)"), self.y_max)
        layout.addRow(hp.make_h_line_with_text("X-axis limits", bold=True))
        layout.addRow(hp.make_label(self, "lower"), self.x_range_min)
        layout.addRow(hp.make_label(self, "upper"), self.x_range_max)
        layout.addRow(self.x_range_reset)
        layout.addRow(hp.make_h_line_with_text("Y-axis limits", bold=True))
        layout.addRow(hp.make_label(self, "lower"), self.y_range_min)
        layout.addRow(hp.make_label(self, "upper"), self.y_range_max)
        layout.addRow(self.y_range_reset)
        layout.addRow(hp.make_h_line_with_text("Axis limit modes", bold=True))
        layout.addRow(self.axis_mode_all)
        layout.addRow(hp.make_label(self, "Limit to top"), self.axis_mode_top)
        layout.addRow(hp.make_label(self, "Limit to bottom"), self.axis_mode_bottom)
        layout.addRow(hp.make_label(self, "Limit to left"), self.axis_mode_left)
        layout.addRow(hp.make_label(self, "Limit to right"), self.axis_mode_right)
        layout.setSpacing(2)

        # setup UI
        self._on_extent_changed()
        self._on_rect_changed()
        self._on_interactive_changed()
        self._on_x_range_changed()
        self._on_y_range_changed()
        self._on_extent_mode_changed()
        self._on_axis_mode_changed()
        self._on_aspect_changed()

    def on_change_interactive(self):
        """Update interactivity."""
        self.ref_viewer().camera.mouse_pan = self.mouse_pan_checkbox.isChecked()
        self.ref_viewer().camera.mouse_zoom = self.mouse_zoom_checkbox.isChecked()

    def _on_interactive_changed(self, _event=None):
        """Update interactive checkbox."""
        with self.ref_viewer().camera.events.mouse_pan.blocker():
            self.mouse_pan_checkbox.setChecked(self.ref_viewer().camera.mouse_pan)
        with self.ref_viewer().camera.events.mouse_zoom.blocker():
            self.mouse_zoom_checkbox.setChecked(self.ref_viewer().camera.mouse_zoom)

    def on_change_extent_mode(self):
        """Update interactivity."""
        self.ref_viewer().camera.extent_mode = self.extent_mode.currentData()

    def _on_extent_mode_changed(self, _event=None):
        """Update interactive checkbox."""
        with self.ref_viewer().camera.events.extent_mode.blocker():
            hp.set_combobox_current_index(self.extent_mode, self.ref_viewer().camera.extent_mode)

    def on_reset_axis_mode(self):
        """Reset axis mode."""
        self.ref_viewer().camera.axis_mode = (CameraMode.ALL,)

    def on_reset_x_range(self):
        """Reset axis mode."""
        self.ref_viewer().camera.x_range = None

    def on_reset_y_range(self):
        """Reset axis mode."""
        self.ref_viewer().camera.y_range = None

    def on_change_axis_mode(self):
        """Update axis mode."""
        axis_mode = []
        if self.axis_mode_top.isChecked():
            axis_mode.append(CameraMode.LOCK_TO_TOP)
        if self.axis_mode_bottom.isChecked():
            axis_mode.append(CameraMode.LOCK_TO_BOTTOM)
        if self.axis_mode_left.isChecked():
            axis_mode.append(CameraMode.LOCK_TO_LEFT)
        if self.axis_mode_right.isChecked():
            axis_mode.append(CameraMode.LOCK_TO_RIGHT)
        if not axis_mode:
            axis_mode.append(CameraMode.ALL)
        self.ref_viewer().camera.axis_mode = tuple(axis_mode)

    def _on_axis_mode_changed(self, _event=None):
        """Update interactive checkbox."""
        with self.ref_viewer().camera.events.axis_mode.blocker():
            with hp.qt_signals_blocked(self.axis_mode_top):
                self.axis_mode_top.setChecked(CameraMode.LOCK_TO_TOP in self.ref_viewer().camera.axis_mode)
            with hp.qt_signals_blocked(self.axis_mode_bottom):
                self.axis_mode_bottom.setChecked(CameraMode.LOCK_TO_BOTTOM in self.ref_viewer().camera.axis_mode)
            with hp.qt_signals_blocked(self.axis_mode_left):
                self.axis_mode_left.setChecked(CameraMode.LOCK_TO_LEFT in self.ref_viewer().camera.axis_mode)
            with hp.qt_signals_blocked(self.axis_mode_right):
                self.axis_mode_right.setChecked(CameraMode.LOCK_TO_RIGHT in self.ref_viewer().camera.axis_mode)

    def _on_aspect_changed(self, _event=None):
        """Update aspect."""
        with self.ref_viewer().camera.events.aspect.blocker():
            self.aspect.setValue(0 if self.ref_viewer().camera.aspect is None else self.ref_viewer().camera.aspect)

    def on_change_aspect(self):
        """Update aspect."""
        value = self.aspect.value()
        if value == 0:
            value = None
        self.ref_viewer().camera.aspect = value

    def on_change_rect(self):
        """Update min/max."""
        self.ref_viewer().camera.rect = [
            self.x_min.value(),
            self.x_max.value(),
            self.y_min.value(),
            self.y_max.value(),
        ]

    def _on_extent_changed(self, _event=None):
        """Update min/max controls."""
        with self.ref_viewer().camera.events.extent.blocker():
            x0, x1, y0, y1 = self.ref_viewer().camera.extent
            self.extent_x_min.setValue(x0)
            self.extent_x_max.setValue(x1)
            self.extent_y_min.setValue(y0)
            self.extent_y_max.setValue(y1)

    def on_change_extent(self):
        """Update min/max."""
        self.ref_viewer().camera.extent = [
            self.extent_x_min.value(),
            self.extent_x_max.value(),
            self.extent_y_min.value(),
            self.extent_y_max.value(),
        ]

    def _on_rect_changed(self, _event=None):
        """Update min/max controls."""
        with self.ref_viewer().camera.events.rect.blocker():
            x0, x1, y0, y1 = self.ref_viewer().camera.rect
            self.x_min.setValue(x0)
            self.x_max.setValue(x1)
            self.y_min.setValue(y0)
            self.y_max.setValue(y1)

    def on_change_x_range(self):
        """Update x-range"""
        min_val, max_val = parse_widget_to_value(self.x_range_min), parse_widget_to_value(self.x_range_max)
        self.ref_viewer().camera.set_x_range(min_val, max_val)

    def _on_x_range_changed(self, _event=None):
        """Update x-range controls."""
        with self.ref_viewer().camera.events.x_range.blocker():
            min_val, max_val = parse_range_to_text(self.ref_viewer().camera.x_range)
            self.x_range_min.setText(min_val)
            self.x_range_max.setText(max_val)

    def on_change_y_range(self):
        """Update y-range."""
        min_val, max_val = parse_widget_to_value(self.y_range_min), parse_widget_to_value(self.y_range_max)
        self.ref_viewer().camera.set_y_range(min_val, max_val)

    def _on_y_range_changed(self, _event=None):
        """Update y-range controls."""
        with self.ref_viewer().camera.events.y_range.blocker():
            min_val, max_val = parse_range_to_text(self.ref_viewer().camera.y_range)
            self.y_range_min.setText(min_val)
            self.y_range_max.setText(max_val)

    def close(self):
        """Disconnect events when widget is closing."""
        disconnect_events(self.ref_viewer().axis.events, self)
        super().close()


class QtCameraControls(QtFramelessPopup):
    """Popup to control camera model"""

    def __init__(self, viewer: "ViewerModel", parent=None):
        self.ref_viewer = ref(viewer)

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("camera")
        self.setMouseTracking(True)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel"""
        widget = QtCameraWidget(self.ref_viewer(), self)
        layout = QFormLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)
        layout.addRow(self._make_move_handle("Camera controls"))
        layout.addRow(widget)
        return layout


def parse_widget_to_value(widget):
    """Parse value."""
    value = widget.text()
    if value:
        return float(value)
    return None


def parse_range_to_text(limits):
    """Return range to text."""
    if limits is None:
        return "", ""
    return str(limits[0]), str(limits[1])
