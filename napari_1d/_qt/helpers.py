"""Helper functions to easily create UI elements."""
from typing import Dict, List, Optional, OrderedDict, Union

from qtpy.QtWidgets import QButtonGroup
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont
from qtpy.QtWidgets import QCheckBox, QComboBox, QLabel, QLineEdit, QSizePolicy, QSlider, QSpacerItem, QWidget

from ..utils.system import IS_WIN
from .widgets.qt_icon_label import QtIconLabel
from .widgets.qt_image_button import QtImagePushButton


def make_v_spacer() -> QSpacerItem:
    """Make vertical QSpacerItem"""
    widget = QSpacerItem(40, 20, QSizePolicy.Preferred, QSizePolicy.Expanding)
    return widget


def make_h_spacer() -> QSpacerItem:
    """Make horizontal QSpacerItem"""
    widget = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Preferred)
    return widget


def make_label_icon(parent, object_name: str, tooltip: str = None) -> QtIconLabel:
    """Make icon label"""
    widget = QtIconLabel(parent=parent, object_name=object_name)
    if tooltip:
        set_tooltip(widget, tooltip)
    return widget


def make_svg_btn(
    parent,
    object_name: str,
    text: str = "",
    tooltip: str = None,
    flat: bool = False,
    checkable: bool = False,
) -> QtImagePushButton:
    """Make button"""
    widget = QtImagePushButton(None, text, parent)
    widget.setObjectName(object_name)
    widget.setText(text)
    if tooltip:
        set_tooltip(widget, tooltip)
    if flat:
        widget.setFlat(flat)
    if checkable:
        widget.setCheckable(checkable)
    return widget


def make_slider(
    parent,
    min_val: float = 0,
    max_val: float = 100,
    step_size: float = 1,
    val: float = 1,
    orientation="horizontal",
    tooltip: str = None,
    is_disabled: bool = False,
    focus_policy: Qt.FocusPolicy = Qt.TabFocus,
) -> QSlider:
    """Make QSlider"""
    orientation = Qt.Horizontal if orientation.lower() else Qt.Vertical
    widget = QSlider(parent)  # noqa
    widget.setRange(min_val, max_val)
    widget.setValue(val)
    widget.setOrientation(orientation)
    widget.setPageStep(step_size)
    widget.setDisabled(is_disabled)
    widget.setFocusPolicy(focus_policy)
    if tooltip:
        set_tooltip(widget, tooltip)
    return widget


def make_checkbox(
    parent, text: str = "", val: bool = False, tooltip: str = None, is_disabled: bool = False
) -> QCheckBox:
    """Make checkbox"""
    widget = QCheckBox(parent)
    widget.setText(text)
    widget.setChecked(val)
    widget.setDisabled(is_disabled)
    if tooltip:
        set_tooltip(widget, tooltip)
    return widget


def set_bold(widget: QWidget, bold: bool = True) -> QWidget:
    """Set text on widget as bold"""
    font = widget.font()
    font.setBold(bold)
    widget.setFont(font)
    return widget


def make_label(
    parent,
    text: str,
    enable_url: bool = False,
    alignment=None,
    wrap: bool = False,
    object_name: str = "",
    is_disabled: bool = False,
    bold: bool = False,
    font_size: Optional[int] = None,
    tooltip: str = None,
) -> QLabel:
    """Make QLabel element"""
    widget = QLabel(parent)
    widget.setText(text)
    widget.setObjectName(object_name)
    widget.setDisabled(is_disabled)
    if enable_url:
        widget.setTextFormat(Qt.RichText)
        widget.setTextInteractionFlags(Qt.TextBrowserInteraction)
        widget.setOpenExternalLinks(True)
    if alignment is not None:
        widget.setAlignment(alignment)
    if bold:
        set_bold(widget, bold)
    if tooltip:
        set_tooltip(widget, tooltip)
    if font_size:
        set_font(widget, font_size=font_size, bold=bold)
    widget.setWordWrap(wrap)
    return widget


def set_tooltip(widget: QWidget, text: str):
    """Set tooltip"""
    widget.setToolTip(text)


def set_font(widget: QWidget, font_size: int = 7, font_weight: int = 50, bold: bool = False):
    """Set font on a widget"""
    font = QFont()
    font.setPointSize(font_size if IS_WIN else font_size + 2)
    font.setWeight(font_weight)
    font.setBold(bold)
    widget.setFont(font)


def make_combobox(parent, items: List[str] = None, tooltip: str = None, is_disabled: bool = False) -> QComboBox:
    """Make QComboBox"""
    widget = QComboBox(parent)
    widget.setDisabled(is_disabled)
    if items:
        widget.addItems(items)
    if tooltip:
        set_tooltip(widget, tooltip)
    return widget


def set_combobox_data(widget: QComboBox, data: Union[Dict, OrderedDict], current_item: Optional = None):
    """Set data/value on combobox"""
    for index, (data, text) in enumerate(data.items()):
        if not isinstance(data, str):
            data = data.value
        widget.addItem(text, data)

        if current_item is not None:
            if current_item == data or current_item == text:
                widget.setCurrentIndex(index)


def set_current_combobox_index(widget: QComboBox, current_data):
    """Set current index on combobox"""
    for index in range(widget.count()):
        if widget.itemData(index) == current_data:
            widget.setCurrentIndex(index)
            break


def make_line_edit(
    parent,
    text: str = "",
    tooltip: str = None,
    placeholder: str = "",
    is_disabled: bool = False,
) -> QLineEdit:
    """Make QLineEdit"""
    widget = QLineEdit(parent)  # noqa
    widget.setText(text)
    widget.setDisabled(is_disabled)
    if tooltip:
        set_tooltip(widget, tooltip)
    widget.setPlaceholderText(placeholder)
    return widget


def make_radio_btn_group(parent, radio_buttons) -> QButtonGroup:
    """Make radio button group"""
    widget = QButtonGroup(parent)
    for btn_id, radio_btn in enumerate(radio_buttons):
        widget.addButton(radio_btn, btn_id)
    return widget
