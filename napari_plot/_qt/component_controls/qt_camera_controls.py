"""Camera controls"""

from __future__ import annotations

import typing as ty
from weakref import ref

import qtextra.helpers as hp
from napari.utils.events import disconnect_events
from qtextra.widgets.qt_dialog import QtFramelessPopup
from qtpy.QtCore import Qt
from qtpy.QtGui import QDoubleValidator
from qtpy.QtWidgets import QFormLayout, QWidget

from napari_plot._qt.component_controls.qt_grid_cell_selector import GridTarget, QtGridCellSelector, connect_all
from napari_plot.components.camera import EXTENT_MODE_TRANSLATIONS, CameraMode

if ty.TYPE_CHECKING:
    from napari.utils.events import Event

    from napari_plot.components.canvas import PlotGridCell
    from napari_plot.components.viewer_model import ViewerModel

_SHARED_TOOLTIP = "The {name}-axis is shared by all cells - edit it in 'All cells'."


class QtCameraWidget(QWidget):
    """Controls of the camera, for all cells or for one cell of a regular grid.

    In the view of one cell, the extents are the cell's data bounds (read-only), the current limits are the limits
    shown in the cell and the axis limits are the cell's own ``xlim``/``ylim``. Shared axes can only be edited for all
    cells, and the interaction settings (pan/zoom, restriction, aspect, lock modes) are hidden.
    """

    def __init__(self, viewer: ViewerModel, parent: QWidget | None, target: GridTarget = None) -> None:
        super().__init__(parent=parent)
        self.ref_viewer = ref(viewer)
        self.target: GridTarget = None
        self._global_rows: list[QWidget] = []
        self._tooltips: dict[QWidget, str] = {}
        viewer.events.cell_rect.connect(self._on_rect_changed)
        connect_all(viewer.canvas.grid.events, self._on_grid_changed)
        self.cell_selector = QtGridCellSelector(viewer, self)
        self.cell_selector.target_changed.connect(self.set_target)
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
            self,
            tooltip="Lower x-axis range",
            minimum=-1e10,
            maximum=1e10,
            n_decimals=6,
            func=self.on_change_extent,
        )
        self.extent_x_max = hp.make_double_spin_box(
            self,
            tooltip="Upper x-axis range",
            minimum=-1e10,
            maximum=1e10,
            n_decimals=6,
            func=self.on_change_extent,
        )

        self.extent_y_min = hp.make_double_spin_box(
            self,
            tooltip="Lower y-axis range",
            minimum=-1e10,
            maximum=1e10,
            n_decimals=6,
            func=self.on_change_extent,
        )
        self.extent_y_max = hp.make_double_spin_box(
            self,
            tooltip="Upper y-axis range",
            minimum=-1e10,
            maximum=1e10,
            n_decimals=6,
            func=self.on_change_extent,
        )

        # ranges
        self.x_min = hp.make_double_spin_box(
            self,
            tooltip="Lower x-axis range",
            minimum=-1e10,
            maximum=1e10,
            n_decimals=6,
            func=self.on_change_rect,
        )
        self.x_max = hp.make_double_spin_box(
            self,
            tooltip="Upper x-axis range",
            minimum=-1e10,
            maximum=1e10,
            n_decimals=6,
            func=self.on_change_rect,
        )

        self.y_min = hp.make_double_spin_box(
            self,
            tooltip="Lower y-axis range",
            minimum=-1e10,
            maximum=1e10,
            n_decimals=6,
            func=self.on_change_rect,
        )
        self.y_max = hp.make_double_spin_box(
            self,
            tooltip="Upper y-axis range",
            minimum=-1e10,
            maximum=1e10,
            n_decimals=6,
            func=self.on_change_rect,
        )

        validator = QDoubleValidator(parent=self)
        self.x_range_min = hp.make_line_edit(
            self,
            tooltip="Lower x-axis range",
            validator=validator,
            func=self.on_change_x_range,
        )
        self.x_range_max = hp.make_line_edit(
            self,
            tooltip="Upper x-axis range",
            validator=validator,
            func=self.on_change_x_range,
        )

        self.y_range_min = hp.make_line_edit(
            self,
            tooltip="Lower x-axis range",
            validator=validator,
            func=self.on_change_y_range,
        )
        self.y_range_max = hp.make_line_edit(
            self,
            tooltip="Upper x-axis range",
            validator=validator,
            func=self.on_change_y_range,
        )

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

        self.reset_x_range_btn = hp.make_btn(self, "Reset x-range", func=self.on_reset_x_range)
        self.reset_y_range_btn = hp.make_btn(self, "Reset y-range", func=self.on_reset_y_range)
        self.reset_all_cells_btn = hp.make_btn(
            self,
            "Reset all cell limits",
            tooltip="Remove the own x/y-axis limits of every grid cell.",
            func=self.on_reset_all_cells,
        )
        axis_modes_header = hp.make_h_line_with_text("Axis limit modes", bold=True)

        layout = self._layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.addRow(self.cell_selector)
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
        layout.addRow(self.reset_x_range_btn)
        layout.addRow(hp.make_h_line_with_text("Y-axis limits", bold=True))
        layout.addRow(hp.make_label(self, "lower"), self.y_range_min)
        layout.addRow(hp.make_label(self, "upper"), self.y_range_max)
        layout.addRow(self.reset_y_range_btn)
        layout.addRow(self.reset_all_cells_btn)
        layout.addRow(axis_modes_header)
        layout.addRow(self.axis_mode_all)
        layout.addRow(hp.make_label(self, "Limit to top"), self.axis_mode_top)
        layout.addRow(hp.make_label(self, "Limit to bottom"), self.axis_mode_bottom)
        layout.addRow(hp.make_label(self, "Limit to left"), self.axis_mode_left)
        layout.addRow(hp.make_label(self, "Limit to right"), self.axis_mode_right)
        layout.setSpacing(2)
        self._global_rows = [
            self.mouse_zoom_checkbox,
            self.mouse_pan_checkbox,
            self.extent_mode,
            self.aspect,
            self.reset_all_cells_btn,
            axis_modes_header,
            self.axis_mode_all,
            self.axis_mode_top,
            self.axis_mode_bottom,
            self.axis_mode_left,
            self.axis_mode_right,
        ]

        # setup UI
        self._on_extent_changed()
        self._on_rect_changed()
        self._on_interactive_changed()
        self._on_x_range_changed()
        self._on_y_range_changed()
        self._on_extent_mode_changed()
        self._on_axis_mode_changed()
        self._on_aspect_changed()
        self.set_target(None)
        if target is not None:
            self.cell_selector.set_target(target)

    # -- target -----------------------------------------------------------------------------------------------------

    def set_target(self, target: GridTarget) -> None:
        """Edit the camera of all cells (``None``) or the limits of the grid cell at ``(row, column)``."""
        self.target = target
        for widget in self._global_rows:
            self._layout.setRowVisible(widget, target is None)
        for widget in (self.extent_x_min, self.extent_x_max, self.extent_y_min, self.extent_y_max):
            widget.setReadOnly(target is not None)
        self._on_grid_changed()

    def _cell_target(self) -> GridTarget:
        """Return the target cell while it is shown in a regular grid, else None (all cells)."""
        viewer = self.ref_viewer()
        if self.target is None or viewer is None or self.target not in viewer._grid_cells():
            return None
        return self.target

    def _cell(self, create: bool = False) -> PlotGridCell | None:
        """Return the settings of the target cell (created when ``create``), or None for all cells."""
        target = self._cell_target()
        if target is None:
            return None
        grid = self.ref_viewer().canvas.grid
        return grid.cell(*target) if create else grid._find_cell(*target)

    def _on_grid_changed(self, _event: Event | None = None) -> None:
        """Show the values of the target and disable the axes it shares with the other cells."""
        viewer = self.ref_viewer()
        if viewer is None:
            return
        grid = viewer.canvas.grid
        cell_view = self._cell_target() is not None
        for name, shared, widgets in (
            ("x", grid.sharex, (self.x_min, self.x_max, self.x_range_min, self.x_range_max, self.reset_x_range_btn)),
            ("y", grid.sharey, (self.y_min, self.y_max, self.y_range_min, self.y_range_max, self.reset_y_range_btn)),
        ):
            locked = cell_view and shared
            for widget in widgets:
                default = self._tooltips.setdefault(widget, widget.toolTip())
                widget.setEnabled(not locked)
                widget.setToolTip(_SHARED_TOOLTIP.format(name=name) if locked else default)
        self.reset_all_cells_btn.setEnabled(any(cell.xlim or cell.ylim for cell in grid.cells))
        self._on_extent_changed()
        self._on_rect_changed()
        self._on_x_range_changed()
        self._on_y_range_changed()

    def on_reset_all_cells(self) -> None:
        """Remove the own x/y-axis limits of every grid cell."""
        for cell in self.ref_viewer().canvas.grid.cells:
            cell.clear_overrides(("xlim", "ylim"))

    def _set_cell_limits(self, name: str, lower: float | None, upper: float | None) -> None:
        """Set the own ``xlim``/``ylim`` of the target cell; a missing value comes from the cell's data bounds."""
        if lower is None and upper is None:
            limits = None
        else:
            index = 0 if name == "x" else 2
            bounds = self.ref_viewer()._cell_extent(*self.target)[index : index + 2]
            limits = (bounds[0] if lower is None else lower, bounds[1] if upper is None else upper)
        try:
            setattr(self._cell(create=True), f"{name}lim", limits)
        except ValueError:
            self._on_grid_changed()

    # -- editors ----------------------------------------------------------------------------------------------------

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
        """Reset the x-axis limits of all cells, or the own x limits of the target cell."""
        if self._cell_target() is None:
            self.ref_viewer().camera.x_range = None
        elif (cell := self._cell()) is not None:
            cell.xlim = None

    def on_reset_y_range(self):
        """Reset the y-axis limits of all cells, or the own y limits of the target cell."""
        if self._cell_target() is None:
            self.ref_viewer().camera.y_range = None
        elif (cell := self._cell()) is not None:
            cell.ylim = None

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
        rect = [self.x_min.value(), self.x_max.value(), self.y_min.value(), self.y_max.value()]
        target = self._cell_target()
        if target is None:
            self.ref_viewer().camera.rect = rect
            return
        try:
            self.ref_viewer().set_cell_rect(*target, *rect)
        except ValueError:
            self._on_rect_changed()

    def _on_extent_changed(self, _event=None):
        """Update min/max controls."""
        viewer = self.ref_viewer()
        target = self._cell_target()
        extent = viewer.camera.extent if target is None else viewer._cell_extent(*target)
        widgets = self.extent_x_min, self.extent_x_max, self.extent_y_min, self.extent_y_max
        for widget, value in zip(widgets, extent, strict=True):
            with hp.qt_signals_blocked(widget):
                widget.setValue(value)

    def on_change_extent(self):
        """Update min/max."""
        if self._cell_target() is not None:
            return
        self.ref_viewer().camera.extent = [
            self.extent_x_min.value(),
            self.extent_x_max.value(),
            self.extent_y_min.value(),
            self.extent_y_max.value(),
        ]

    def _on_rect_changed(self, _event=None):
        """Update min/max controls."""
        viewer = self.ref_viewer()
        target = self._cell_target()
        rect = viewer.camera.rect if target is None else viewer.cell_rect(*target)
        widgets = self.x_min, self.x_max, self.y_min, self.y_max
        for widget, value in zip(widgets, rect, strict=True):
            with hp.qt_signals_blocked(widget):
                widget.setValue(value)

    def on_change_x_range(self):
        """Update x-range"""
        min_val, max_val = parse_widget_to_value(self.x_range_min), parse_widget_to_value(self.x_range_max)
        if self._cell_target() is None:
            self.ref_viewer().camera.set_x_range(min_val, max_val)
        else:
            self._set_cell_limits("x", min_val, max_val)

    def _on_x_range_changed(self, _event=None):
        """Update x-range controls."""
        self._show_range(self.x_range_min, self.x_range_max, "x")

    def on_change_y_range(self):
        """Update y-range."""
        min_val, max_val = parse_widget_to_value(self.y_range_min), parse_widget_to_value(self.y_range_max)
        if self._cell_target() is None:
            self.ref_viewer().camera.set_y_range(min_val, max_val)
        else:
            self._set_cell_limits("y", min_val, max_val)

    def _on_y_range_changed(self, _event=None):
        """Update y-range controls."""
        self._show_range(self.y_range_min, self.y_range_max, "y")

    def _show_range(self, lower: QWidget, upper: QWidget, name: str) -> None:
        """Show the fixed limits of all cells (camera range) or of the target cell (its own limits)."""
        cell = self._cell()
        limits = getattr(self.ref_viewer().camera, f"{name}_range") if self._cell_target() is None else None
        if cell is not None:
            limits = getattr(cell, f"{name}lim")
        for widget, text in zip((lower, upper), parse_range_to_text(limits), strict=True):
            with hp.qt_signals_blocked(widget):
                widget.setText(text)

    def close(self):
        """Disconnect events when widget is closing."""
        _disconnect_camera_events(self.ref_viewer(), self)
        super().close()


def _disconnect_camera_events(viewer: ViewerModel | None, widget: QtCameraWidget) -> None:
    """Disconnect the camera widget from the viewer's camera, grid, cell limit and layer events."""
    if viewer is not None:
        disconnect_events(viewer.camera.events, widget)
        disconnect_events(viewer.canvas.grid.events, widget)
        viewer.events.cell_rect.disconnect(widget._on_rect_changed)
    widget.cell_selector.disconnect_viewer()


class QtCameraControls(QtFramelessPopup):
    """Popup to control camera model"""

    def __init__(self, viewer: ViewerModel, parent: QWidget | None = None, target: GridTarget = None) -> None:
        self.ref_viewer = ref(viewer)
        self._target = target

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("camera")
        self.setMouseTracking(True)
        viewer_ref, camera_widget = self.ref_viewer, self.camera_widget
        self.destroyed.connect(lambda *_args: _disconnect_camera_events(viewer_ref(), camera_widget))

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel"""
        self.camera_widget = QtCameraWidget(self.ref_viewer(), self, target=self._target)
        layout = QFormLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)
        layout.addRow(self._make_move_handle("Camera controls"))
        layout.addRow(self.camera_widget)
        return layout

    def _on_teardown(self) -> None:
        """Disconnect camera events from the inner widget on close."""
        _disconnect_camera_events(self.ref_viewer(), self.camera_widget)


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
