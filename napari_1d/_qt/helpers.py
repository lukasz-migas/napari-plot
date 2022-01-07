"""Helper functions to easily create UI elements."""
import typing as ty
from contextlib import contextmanager

from qtpy.QtCore import Qt
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (
    QActionGroup,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpacerItem,
    QWidget,
)

from ..utils.system import IS_WIN
from .widgets.qt_icon_button import QtImagePushButton
from .widgets.qt_icon_label import QtQtaLabel
from .widgets.qt_line import QtHorzLine, QtVertLine


def make_v_spacer() -> QSpacerItem:
    """Make vertical QSpacerItem."""
    widget = QSpacerItem(40, 20, QSizePolicy.Preferred, QSizePolicy.Expanding)
    return widget


def make_h_spacer() -> QSpacerItem:
    """Make horizontal QSpacerItem."""
    widget = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Preferred)
    return widget


def make_qta_label(
    parent: ty.Optional[QWidget], icon_name: str, alignment=None, tooltip: str = None, small: bool = False, **kwargs
):
    """Make QLabel with QtAwesome icon."""
    widget = QtQtaLabel(parent=parent)
    widget.set_qta(icon_name, **kwargs)
    if small:
        widget.set_small()
    if alignment is not None:
        widget.setAlignment(alignment)
    if tooltip:
        widget.setToolTip(tooltip)
    return widget


def make_qta_btn(
    parent: ty.Optional[QWidget],
    icon_name: str,
    tooltip: str = None,
    flat: bool = False,
    checkable: bool = False,
    size: ty.Optional[ty.Tuple[int, int]] = None,
    size_name: ty.Optional[str] = None,
    **kwargs,
) -> QtImagePushButton:
    """Make QPushButton with QtAwesome icon."""
    widget = QtImagePushButton(parent=parent)
    widget.set_qta(icon_name, **kwargs)
    widget.set_size_name(size_name)
    if size_name:
        widget.set_size_name(size_name)
    if size and len(size) == 2:
        widget.set_size(size)
    if tooltip:
        widget.setToolTip(tooltip)
    if flat:
        widget.setFlat(flat)
    if checkable:
        widget.setCheckable(checkable)
    return widget


def make_slider(
    parent: ty.Optional[QWidget],
    min_value: int = 0,
    max_value: int = 100,
    step_size: int = 1,
    value: int = 1,
    orientation="horizontal",
    tooltip: str = None,
    focus_policy: Qt.FocusPolicy = Qt.TabFocus,
) -> QSlider:
    """Make QSlider."""
    orientation = Qt.Horizontal if orientation.lower() else Qt.Vertical
    widget = QSlider(parent)  # noqa
    widget.setRange(min_value, max_value)
    widget.setValue(value)
    widget.setOrientation(orientation)
    widget.setPageStep(step_size)
    widget.setFocusPolicy(focus_policy)
    if tooltip:
        widget.setToolTip(tooltip)
    return widget


def make_checkbox(
    parent: ty.Optional[QWidget],
    text: str = "",
    val: bool = False,
    tooltip: str = None,
) -> QCheckBox:
    """Make QCheckBox"""
    widget = QCheckBox(parent)
    widget.setText(text)
    widget.setChecked(val)
    if tooltip:
        widget.setToolTip(tooltip)
    return widget


def set_bold(widget: QWidget, bold: bool = True):
    """Set text of particular widget bold."""
    font = widget.font()
    font.setBold(bold)
    widget.setFont(font)


def set_font(widget: QWidget, font_size: int = 7, font_weight: int = 50, bold: bool = False):
    """Set font with specified font size, font weight and boldness for particular widget."""
    font = QFont()
    font.setPointSize(font_size if IS_WIN else font_size + 2)
    font.setWeight(font_weight)
    font.setBold(bold)
    widget.setFont(font)


def make_label(
    parent: ty.Optional[QWidget],
    text: str,
    enable_url: bool = False,
    alignment=None,
    wrap: bool = False,
    object_name: str = "",
    bold: bool = False,
    font_size: ty.Optional[int] = None,
    tooltip: str = None,
) -> QLabel:
    """Make QLabel."""
    widget = QLabel(parent)
    widget.setText(text)
    widget.setObjectName(object_name)
    if enable_url:
        widget.setTextFormat(Qt.RichText)
        widget.setTextInteractionFlags(Qt.TextBrowserInteraction)
        widget.setOpenExternalLinks(True)
    if alignment is not None:
        widget.setAlignment(alignment)
    if bold:
        set_bold(widget, bold)
    if tooltip:
        widget.setToolTip(tooltip)
    if font_size:
        set_font(widget, font_size=font_size, bold=bold)
    widget.setWordWrap(wrap)
    return widget


def make_combobox(parent: ty.Optional[QWidget], items: ty.List[str] = None, tooltip: str = None) -> QComboBox:
    """Make QComboBox with specified items."""
    widget = QComboBox(parent)
    if items:
        widget.addItems(items)
    if tooltip:
        widget.setToolTip(tooltip)
    return widget


def set_combobox_data(widget: QComboBox, data: ty.Union[ty.Dict, ty.OrderedDict], current_item: ty.Optional = None):
    """Set data/value on combobox"""
    for index, (data, text) in enumerate(data.items()):
        if not isinstance(data, str):
            data = data.value
        widget.addItem(text, data)

        if current_item is not None:
            if current_item == data or current_item == text:
                widget.setCurrentIndex(index)


def set_combobox_current_index(widget: QComboBox, current_data: ty.Any):
    """Set current index on combobox."""
    for index in range(widget.count()):
        if widget.itemData(index) == current_data:
            widget.setCurrentIndex(index)
            break


def make_line_edit(
    parent: ty.Optional[QWidget],
    text: str = "",
    tooltip: str = None,
    placeholder: str = "",
) -> QLineEdit:
    """Make QLineEdit/"""
    widget = QLineEdit(parent)  # noqa
    widget.setText(text)
    if tooltip:
        widget.setToolTip(tooltip)
    widget.setPlaceholderText(placeholder)
    return widget


def make_radio_btn_group(parent: ty.Optional[QWidget], radio_buttons: ty.Iterable[QPushButton]) -> QButtonGroup:
    """Make radio button group."""
    widget = QButtonGroup(parent)
    for btn_id, radio_btn in enumerate(radio_buttons):
        widget.addButton(radio_btn, btn_id)
    return widget


def make_h_line(parent: ty.Optional[QWidget]) -> QtHorzLine:
    """Make horizontal line. Styling of the `QtHorzLine` is setup in one of the stylesheets."""
    widget = QtHorzLine(parent)
    return widget


def make_v_line(parent: ty.Optional[QWidget]) -> QtVertLine:
    """Make horizontal line. Styling of the `QtVertLine` is setup in one of the stylesheets."""
    widget = QtVertLine(parent)
    return widget


def make_menu_group(parent: QWidget, *actions):
    """Make actions group"""
    group = QActionGroup(parent)
    for action in actions:
        group.addAction(action)
    return group


@contextmanager
def qt_signals_blocked(obj):
    """Context manager to temporarily block signals from `obj`"""
    obj.blockSignals(True)
    yield
    obj.blockSignals(False)
