"""X/Y-axis controls"""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any
from weakref import ref

import qtextra.helpers as hp
from napari._qt.utils import qt_signals_blocked, set_widgets_enabled_with_opacity
from napari._qt.widgets.qt_color_swatch import QColorSwatch
from napari.utils.events import disconnect_events
from qtextra.widgets.qt_dialog import QtFramelessPopup
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout, QLineEdit, QWidget

from napari_plot._qt.component_controls.qt_grid_cell_selector import GridTarget, QtGridCellSelector, connect_all
from napari_plot.components.axis import AxisScale

if TYPE_CHECKING:
    from weakref import ReferenceType

    from napari.utils.events import Event

    from napari_plot.components.canvas import PlotGridCell
    from napari_plot.components.viewer_model import ViewerModel

# axis settings that this widget can set for one grid cell
CELL_FIELDS: tuple[str, ...] = (
    "x_visible",
    "y_visible",
    "x_label",
    "y_label",
    "x_scale",
    "y_scale",
    "x_categories",
    "y_categories",
    "x_inverted",
    "y_inverted",
    "x_tick_rotation",
    "label_size",
    "tick_size",
    "label_color",
    "tick_color",
)


class QtAxisWidget(QWidget):
    """Controls of the x/y-axes, for all cells (the viewer's axis) or for one cell of a regular grid.

    In the view of one cell, each field shows the value the cell uses; editing it makes the cell override the viewer
    setting, and the button next to an overridden field makes it follow the viewer setting again. Settings that only
    exist for all cells (margins, maximum sizes) are hidden.
    """

    def __init__(self, viewer: ViewerModel, parent: QWidget | None, target: GridTarget = None) -> None:
        super().__init__(parent=parent)
        self.ref_viewer = ref(viewer)
        self.target: GridTarget = None
        self._reset_buttons: dict[str, QWidget] = {}
        self._global_rows: list[QWidget] = []
        self._cell_rows: list[QWidget] = []
        connect_all(viewer.axis.events, self._sync)
        viewer.events.theme.connect(self._sync)
        connect_all(viewer.canvas.grid.events, self._sync)

        self.cell_selector = QtGridCellSelector(viewer, self)
        self.cell_selector.target_changed.connect(self.set_target)

        self.visible_checkbox = hp.make_checkbox(self, "", value=viewer.axis.visible, tooltip="Show/hide x/y-axes")
        self.visible_checkbox.stateChanged.connect(self.on_change_visible)
        self.x_visible_checkbox = self._make_cell_checkbox("x_visible", "Show/hide the x-axis of this cell")
        self.y_visible_checkbox = self._make_cell_checkbox("y_visible", "Show/hide the y-axis of this cell")

        self.x_axis_edit = hp.make_line_edit(self, viewer.axis.x_label, placeholder="X-axis label...")
        self.x_axis_edit.editingFinished.connect(partial(self.on_change_label, "x"))
        self.y_axis_edit = hp.make_line_edit(self, viewer.axis.y_label, placeholder="Y-axis label...")
        self.y_axis_edit.editingFinished.connect(partial(self.on_change_label, "y"))

        scales = [scale.value for scale in AxisScale]
        self.x_scale_combobox = hp.make_combobox(
            self, items=scales, value=viewer.axis.x_scale.value, tooltip="Scale used by the x-axis."
        )
        self.x_scale_combobox.currentTextChanged.connect(partial(self.on_change_scale, "x"))
        self.y_scale_combobox = hp.make_combobox(
            self, items=scales, value=viewer.axis.y_scale.value, tooltip="Scale used by the y-axis."
        )
        self.y_scale_combobox.currentTextChanged.connect(partial(self.on_change_scale, "y"))

        self.x_categories_edit = hp.make_line_edit(self, placeholder="Comma-separated x categories...")
        self.x_categories_edit.editingFinished.connect(partial(self.on_change_categories, "x"))
        self.y_categories_edit = hp.make_line_edit(self, placeholder="Comma-separated y categories...")
        self.y_categories_edit.editingFinished.connect(partial(self.on_change_categories, "y"))

        self.x_inverted_checkbox = self._make_cell_checkbox("x_inverted", "Show the x-axis from high to low values")
        self.y_inverted_checkbox = self._make_cell_checkbox("y_inverted", "Show the y-axis from high to low values")
        self.x_tick_rotation_spin = hp.make_slider_with_text(
            self, min_value=-90, max_value=90, step_size=15, value=0, tooltip="Rotation of the x tick labels."
        )
        self.x_tick_rotation_spin.valueChanged.connect(lambda value: self._set("x_tick_rotation", float(value)))

        self.x_label_margin_spin = hp.make_slider_with_text(
            self, min_value=10, max_value=120, step_size=5, value=viewer.axis.x_label_margin
        )
        self.x_label_margin_spin.valueChanged.connect(self.on_change_label_margin)
        self.y_label_margin_spin = hp.make_slider_with_text(
            self, min_value=10, max_value=120, step_size=5, value=viewer.axis.y_label_margin
        )
        self.y_label_margin_spin.valueChanged.connect(self.on_change_label_margin)

        self.label_color_swatch = QColorSwatch(
            initial_color=viewer.axis.colors_for_theme(viewer.theme)[1],
            tooltip="Click to set label color",
        )
        self.label_color_swatch.color_changed.connect(self.on_change_label_color)
        self.label_font_size = hp.make_double_slider_with_text(
            self, min_value=4, max_value=30, step_size=1, value=viewer.axis.label_size
        )
        self.label_font_size.valueChanged.connect(self.on_change_label_font_size)
        self.tick_color_swatch = QColorSwatch(
            initial_color=viewer.axis.colors_for_theme(viewer.theme)[0],
            tooltip="Click to set tick color",
        )
        self.tick_color_swatch.color_changed.connect(self.on_change_tick_color)
        self.tick_font_size = hp.make_double_slider_with_text(
            self, min_value=4, max_value=30, step_size=1, value=viewer.axis.tick_size
        )
        self.tick_font_size.valueChanged.connect(self.on_change_tick_font_size)

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

        self.reset_cell_btn = hp.make_btn(
            self, "Reset cell to global", tooltip="Use the settings of all cells in this cell.", func=self.on_reset_cell
        )
        self.reset_all_cells_btn = hp.make_btn(
            self,
            "Reset all cell overrides",
            tooltip="Make every grid cell use the settings of all cells.",
            func=self.on_reset_all_cells,
        )

        layout = self._layout = QFormLayout(self)
        layout.addRow(self.cell_selector)
        self._add_row("Visible", self.visible_checkbox, scope="global")
        self._add_row("X-axis visible", self.x_visible_checkbox, "x_visible", scope="cell")
        self._add_row("X-axis label", self.x_axis_edit, "x_label")
        self._add_row("X-axis scale", self.x_scale_combobox, "x_scale")
        self._add_row("X-axis categories", self.x_categories_edit, "x_categories")
        self._add_row("X-axis inverted", self.x_inverted_checkbox, "x_inverted")
        self._add_row("X tick rotation", self.x_tick_rotation_spin, "x_tick_rotation")
        self._add_row("X-axis label margin", self.x_label_margin_spin, scope="global")
        self._add_row("X-axis tick margin", self.x_tick_margin_spin, scope="global")
        layout.addRow(hp.make_h_line(self))
        self._add_row("Y-axis visible", self.y_visible_checkbox, "y_visible", scope="cell")
        self._add_row("Y-axis label", self.y_axis_edit, "y_label")
        self._add_row("Y-axis scale", self.y_scale_combobox, "y_scale")
        self._add_row("Y-axis categories", self.y_categories_edit, "y_categories")
        self._add_row("Y-axis inverted", self.y_inverted_checkbox, "y_inverted")
        self._add_row("Y-axis label margin", self.y_label_margin_spin, scope="global")
        self._add_row("Y-axis tick margin", self.y_tick_margin_spin, scope="global")
        layout.addRow(hp.make_h_line(self))
        self._add_row("Label color", self.label_color_swatch, "label_color")
        self._add_row("Label font size", self.label_font_size, "label_size")
        self._add_row("Tick color", self.tick_color_swatch, "tick_color")
        self._add_row("Tick font size", self.tick_font_size, "tick_size")
        self._add_row("Max height", self.x_max_size_spin, scope="global")
        self._add_row("Max width", self.y_max_size_spin, scope="global")
        layout.addRow(self.reset_cell_btn)
        self._cell_rows.append(self.reset_cell_btn)
        layout.addRow(self.reset_all_cells_btn)
        self._global_rows.append(self.reset_all_cells_btn)
        layout.setSpacing(2)

        set_widgets_enabled_with_opacity(self, [self.x_max_size_spin, self.y_max_size_spin], False)
        self.set_target(None)
        if target is not None:
            self.cell_selector.set_target(target)

    def _add_row(self, label: str, editor: QWidget, field: str | None = None, *, scope: str = "both") -> None:
        """Add a row; a per-cell ``field`` gets a button that makes the cell follow the viewer setting again."""
        widget = editor
        if field is not None:
            button = hp.make_qta_btn(
                self,
                "mdi6.restore",
                tooltip="Use the setting of all cells",
                func=partial(self.on_reset_field, field),
                small=True,
                retain_size=True,
            )
            self._reset_buttons[field] = button
            widget = QWidget(self)
            hp.make_h_layout(editor, button, stretch_id=(0,), spacing=2, margin=0, parent=widget)
        self._layout.addRow(hp.make_label(self, label), widget)
        if scope == "global":
            self._global_rows.append(widget)
        elif scope == "cell":
            self._cell_rows.append(widget)

    # -- target -----------------------------------------------------------------------------------------------------

    def set_target(self, target: GridTarget) -> None:
        """Edit the settings of all cells (``None``) or of the grid cell at ``(row, column)``."""
        self.target = target
        for widget in self._global_rows:
            self._layout.setRowVisible(widget, target is None)
        for widget in self._cell_rows:
            self._layout.setRowVisible(widget, target is not None)
        self._sync()

    def _cell(self, create: bool = False) -> PlotGridCell | None:
        """Return the settings of the target cell (created when ``create``), or None for all cells."""
        if self.target is None:
            return None
        grid = self.ref_viewer().canvas.grid
        return grid.cell(*self.target) if create else grid._find_cell(*self.target)

    def _value(self, name: str) -> Any:
        """Return the value of an axis setting that the target uses."""
        axis = self.ref_viewer().axis
        cell = self._cell()
        if name in ("x_scale", "y_scale") and cell is not None:
            return cell.axis_scale(name[0], axis)
        value = getattr(cell, name, None)
        if value is not None:
            return value
        if name in ("x_visible", "y_visible"):
            return True
        return getattr(axis, name)

    def _set(self, name: str, value: Any) -> None:
        """Set an axis setting of the viewer, or override it in the target cell."""
        if self.target is None:
            setattr(self.ref_viewer().axis, name, value)
        else:
            setattr(self._cell(create=True), name, value)

    def _make_cell_checkbox(self, name: str, tooltip: str) -> QWidget:
        """Make a checkbox that sets the boolean axis setting ``name``."""
        checkbox = hp.make_checkbox(self, "", tooltip=tooltip)
        checkbox.stateChanged.connect(lambda _state: self._set(name, checkbox.isChecked()))
        return checkbox

    def on_reset_field(self, name: str) -> None:
        """Make the target cell follow the viewer setting ``name`` again."""
        cell = self._cell()
        if cell is not None:
            setattr(cell, name, None)

    def on_reset_cell(self) -> None:
        """Make the target cell follow every axis setting of the viewer again."""
        cell = self._cell()
        if cell is not None:
            cell.clear_overrides(CELL_FIELDS)

    def on_reset_all_cells(self) -> None:
        """Make every grid cell follow the axis settings of the viewer again."""
        for cell in self.ref_viewer().canvas.grid.cells:
            cell.clear_overrides(CELL_FIELDS)

    # -- editors ----------------------------------------------------------------------------------------------------

    def on_change_visible(self) -> None:
        """Change visibility of the axes."""
        self.ref_viewer().axis.visible = self.visible_checkbox.isChecked()

    def on_change_label(self, name: str) -> None:
        """Apply the ``name`` ("x" or "y") axis label once editing finished (Enter or focus out), if it changed."""
        text = (self.x_axis_edit if name == "x" else self.y_axis_edit).text()
        if text != self._value(f"{name}_label"):
            self._set(f"{name}_label", text)

    def on_change_scale(self, name: str, _text: str | None = None) -> None:
        """Apply the selected numeric or categorical scale of the ``name`` ("x" or "y") axis."""
        combobox = self.x_scale_combobox if name == "x" else self.y_scale_combobox
        scale = AxisScale(combobox.currentText())
        if scale is AxisScale.CATEGORICAL and self._value(f"{name}_categories") is None:
            self._sync()  # categories come first
            return
        cell = self._cell(create=self.target is not None)
        if cell is None:
            setattr(self.ref_viewer().axis, f"{name}_scale", scale)
            return
        if scale is not AxisScale.CATEGORICAL and getattr(cell, f"{name}_categories") is not None:
            setattr(cell, f"{name}_categories", None)
        setattr(cell, f"{name}_scale", scale)

    @staticmethod
    def _parse_categories(value: str) -> tuple[str, ...] | None:
        """Parse comma-separated category labels from a line edit."""
        categories = tuple(category.strip() for category in value.split(",") if category.strip())
        return categories or None

    def on_change_categories(self, name: str | None = None) -> None:
        """Apply comma-separated categorical labels to the ``name`` axis (both axes when None)."""
        for axis_name in ("x", "y") if name is None else (name,):
            line_edit = self.x_categories_edit if axis_name == "x" else self.y_categories_edit
            categories = self._parse_categories(line_edit.text())
            if categories != self._value(f"{axis_name}_categories"):
                self._set(f"{axis_name}_categories", categories)

    def on_change_label_margin(self) -> None:
        """Update margin of the x/y-axis label."""
        self.ref_viewer().axis.x_label_margin = self.x_label_margin_spin.value()
        self.ref_viewer().axis.y_label_margin = self.y_label_margin_spin.value()

    def on_change_tick_margin(self) -> None:
        """Update tick margin."""
        self.ref_viewer().axis.x_tick_margin = self.x_tick_margin_spin.value()
        self.ref_viewer().axis.y_tick_margin = self.y_tick_margin_spin.value()

    def on_change_max_size(self) -> None:
        """Change maximum width/height of the axes."""
        self.ref_viewer().axis.x_max_size = self.x_max_size_spin.value()
        self.ref_viewer().axis.y_max_size = self.y_max_size_spin.value()

    def on_change_tick_font_size(self) -> None:
        """Change font size of the tick."""
        self._set("tick_size", self.tick_font_size.value())

    def on_change_tick_color(self, color: str) -> None:
        """Update tick color from color picker user input."""
        self._set("tick_color", color)

    def on_change_label_font_size(self) -> None:
        """Change font size of the label."""
        self._set("label_size", self.label_font_size.value())

    def on_change_label_color(self, color: str) -> None:
        """Update label color from color picker user input."""
        self._set("label_color", color)

    # -- synchronization --------------------------------------------------------------------------------------------

    def _sync(self, _event: Event | None = None) -> None:
        """Show the values the target uses, without writing them back to the models."""
        viewer = self.ref_viewer()
        if viewer is None:
            return
        axis = viewer.axis
        tick_color, label_color = axis.colors_for_theme(viewer.theme)
        cell = self._cell()
        if cell is not None:
            tick_color = tick_color if cell.tick_color is None else cell.tick_color
            label_color = label_color if cell.label_color is None else cell.label_color
        values = {
            self.visible_checkbox: axis.visible,
            self.x_visible_checkbox: self._value("x_visible"),
            self.y_visible_checkbox: self._value("y_visible"),
            self.x_axis_edit: self._value("x_label"),
            self.y_axis_edit: self._value("y_label"),
            self.x_scale_combobox: self._value("x_scale").value,
            self.y_scale_combobox: self._value("y_scale").value,
            self.x_categories_edit: ", ".join(self._value("x_categories") or ()),
            self.y_categories_edit: ", ".join(self._value("y_categories") or ()),
            self.x_inverted_checkbox: self._value("x_inverted"),
            self.y_inverted_checkbox: self._value("y_inverted"),
            self.x_tick_rotation_spin: round(self._value("x_tick_rotation")),
            self.x_label_margin_spin: axis.x_label_margin,
            self.y_label_margin_spin: axis.y_label_margin,
            self.x_tick_margin_spin: axis.x_tick_margin,
            self.y_tick_margin_spin: axis.y_tick_margin,
            self.x_max_size_spin: axis.x_max_size,
            self.y_max_size_spin: axis.y_max_size,
            self.label_font_size: self._value("label_size"),
            self.tick_font_size: self._value("tick_size"),
            self.label_color_swatch: label_color,
            self.tick_color_swatch: tick_color,
        }
        for widget, value in values.items():
            with qt_signals_blocked(widget):
                _set_widget_value(widget, value)
        overridden = set(cell.overrides(CELL_FIELDS)) if cell is not None else set()
        for name, button in self._reset_buttons.items():
            button.setVisible(name in overridden)
        self.reset_cell_btn.setEnabled(bool(overridden))
        self.reset_all_cells_btn.setEnabled(any(other.overrides(CELL_FIELDS) for other in viewer.canvas.grid.cells))

    def disconnect_viewer(self) -> None:
        """Stop following the viewer's axis, theme and grid."""
        _disconnect_axis_events(self.ref_viewer, self)


def _set_widget_value(widget: QWidget, value: Any) -> None:
    """Show ``value`` in an editor; text is only replaced when it changed, so the cursor stays while typing."""
    if isinstance(widget, QLineEdit):
        if widget.text() != value:
            widget.setText(value)
    elif isinstance(widget, QColorSwatch):
        widget.setColor(value)
    elif hasattr(widget, "setChecked"):
        widget.setChecked(bool(value))
    elif hasattr(widget, "setCurrentText"):
        widget.setCurrentText(value)
    else:
        widget.setValue(value)


def _disconnect_axis_events(viewer_ref: ReferenceType[ViewerModel], widget: QtAxisWidget, *_args: object) -> None:
    """Disconnect the axis widget from the viewer's axis, theme, grid and layer events."""
    viewer = viewer_ref()
    if viewer is not None:
        disconnect_events(viewer.axis.events, widget)
        disconnect_events(viewer.canvas.grid.events, widget)
        viewer.events.theme.disconnect(widget)
    widget.cell_selector.disconnect_viewer()


class QtAxisControls(QtFramelessPopup):
    """Popup to control x/y-axis visual"""

    def __init__(self, viewer: ViewerModel, parent: QWidget | None = None, target: GridTarget = None) -> None:
        self.ref_viewer = ref(viewer)
        self._target = target

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("axis")
        self.setMouseTracking(True)
        self.destroyed.connect(partial(_disconnect_axis_events, self.ref_viewer, self.axis_widget))

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel"""
        layout = QFormLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        layout.addRow(self._make_move_handle("Axis controls"))
        self.axis_widget = QtAxisWidget(self.ref_viewer(), self, target=self._target)
        layout.addRow(self.axis_widget)
        return layout

    def _on_teardown(self) -> None:
        """Disconnect the inner widget's listeners when the popup closes."""
        _disconnect_axis_events(self.ref_viewer, self.axis_widget)
