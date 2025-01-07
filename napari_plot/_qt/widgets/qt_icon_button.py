"""QtImagePushButton"""
import typing as ty

import qtawesome
from napari._qt.widgets.qt_mode_buttons import QtModePushButton as _QtModePushButton
from napari._qt.widgets.qt_viewer_buttons import QtViewerPushButton as _QtViewerPushButton
from napari.settings import get_settings
from napari.utils.events.event_utils import connect_no_arg
from napari.utils.theme import _themes, get_theme
from qtpy.QtCore import QSize, Qt, Signal
from qtpy.QtWidgets import QPushButton

from napari_plot.resources import QTA_MAPPING

SIZES = {
    "small": (20, 20),
    "default": (28, 28),
    "medium": (32, 32),
    "large": (40, 40),
    "xlarge": (60, 60),
    "xxlarge": (80, 80),
}


class QtaMixin:
    """Mixin class for buttons."""

    _icon = None
    _qta_data = None

    def set_qta(self, name: str, **kwargs):
        """Set QtAwesome icon."""
        if "." not in name:
            name = QTA_MAPPING[name]
        self._qta_data = (name, kwargs)
        icon = qtawesome.icon(name, **self._qta_data[1], color=get_theme(get_settings().appearance.theme).icon.as_hex())
        self.setIcon(icon)

    def set_size(self, size: ty.Tuple[int, int]):
        """Set size of the button."""
        self.setMinimumSize(QSize(*size))

    def set_size_name(self, size_name: str):
        """Set size of the icon based on pre-defined stylesheet selector."""
        size = QSize(*SIZES[size_name])
        self.setObjectName(size_name)
        self.setMinimumSize(size)
        self.setMaximumSize(size)
        self.setIconSize(size)

    def _update_qta(self):
        """Update qta icon."""
        if self._qta_data:
            name, kwargs = self._qta_data
            self.set_qta(name, **kwargs)

    def _update_from_event(self, event):
        """Update theme based on event."""
        if event.type == "icon":
            self._update_qta()


class QtImagePushButton(QtaMixin, QPushButton):
    """Image button"""

    # Signals
    evt_click = Signal(QPushButton)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        connect_no_arg(get_settings().appearance.events.theme, self, "_update_qta")
        _themes.events.connect(self._update_from_event)

    def mousePressEvent(self, evt) -> None:
        """Mouse press event"""
        if evt.button() == Qt.LeftButton:
            self.evt_click.emit(self)
        super().mousePressEvent(evt)


class QtViewerPushButton(QtaMixin, _QtViewerPushButton):
    """Overwritten class with added support for qtawesome icons."""

    def __init__(self, button_name, tooltip=None, slot=None):
        super().__init__(button_name="", tooltip=tooltip, slot=slot)
        connect_no_arg(get_settings().appearance.events.theme, self, "_update_qta")
        _themes.events.connect(self._update_from_event)
        self.set_qta(button_name)


class QtModePushButton(QtaMixin, _QtModePushButton):
    """Overwritten class with added support for qtawesome icons."""

    def __init__(self, layer, button_name, *, slot=None, tooltip=None):
        super().__init__(layer, "", tooltip=tooltip, slot=slot)
        self.set_qta(button_name)
        self.set_size_name("default")

        connect_no_arg(get_settings().appearance.events.theme, self, "_update_qta")
        _themes.events.connect(self._update_from_event)


class QtModeRadioButton(QtImagePushButton):
    """Overwritten class with added support for qtawesome icons."""

    def __init__(self, layer, button_name, mode, *, tooltip=None, checked=False):
        super().__init__()
        self.layer = layer
        self.setCheckable(True)
        self.setChecked(checked)
        self.set_qta(button_name)
        self.set_size_name("default")
        self.setToolTip(tooltip)
        self.mode = mode
        if mode is not None:
            self.toggled.connect(self._set_mode)

        connect_no_arg(get_settings().appearance.events.theme, self, "_update_qta")
        _themes.events.connect(self._update_from_event)

    def _set_mode(self, value: bool):
        """Toggle the mode associated with the layer."""
        with self.layer.events.mode.blocker(self._set_mode):
            if value:
                self.layer.mode = self.mode
