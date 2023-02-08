"""QtIconLabel"""
import qtawesome
from napari.settings import get_settings
from napari.utils.events.event_utils import connect_no_arg
from napari.utils.theme import _themes, get_theme
from qtpy.QtCore import QSize, Qt
from qtpy.QtWidgets import QLabel

from napari_plot.resources import QTA_MAPPING

SIZES = {
    "small": (20, 20),
    "default": (28, 28),
    "medium": (32, 32),
    "large": (40, 40),
    "xlarge": (60, 60),
    "xxlarge": (80, 80),
}


class QtIconLabel(QLabel):
    """Label with icon"""

    def __init__(self, object_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setObjectName(object_name)


class QtQtaLabel(QtIconLabel):
    """Label"""

    _icon = None
    _qta_data = None

    def __init__(self, *args, **kwargs):
        super().__init__("", *args, **kwargs)
        self._size = QSize(28, 28)
        self.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        connect_no_arg(get_settings().appearance.events.theme, self, "_update_qta")
        _themes.events.connect(self._update_from_event)

    def set_qta(self, name: str, **kwargs):
        """Set QtAwesome icon."""
        if "." not in name:
            name = QTA_MAPPING[name]
        self._qta_data = (name, kwargs)
        icon = qtawesome.icon(
            name, **self._qta_data[1], color=get_theme(get_settings().appearance.theme, False).icon.as_hex()
        )
        self.setIcon(icon)

    def set_size_name(self, size_name: str):
        """Set size of the icon based on pre-defined stylesheet selector."""
        self.setObjectName(size_name)
        self.setIconSize(QSize(*SIZES[size_name]))

    def _update_qta(self):
        """Update qta icon."""
        if self._qta_data:
            name, kwargs = self._qta_data
            self.set_qta(name, **kwargs)

    def _update_from_event(self, event):
        """Update theme based on event."""
        if event.type == "icon":
            self._update_qta()

    def setIcon(self, _icon):
        """
        set a new icon()

        Parameters
        ----------
        _icon: qtawesome.icon
            icon to set
        """
        self._icon = _icon
        self.setPixmap(_icon.pixmap(self._size))

    def setIconSize(self, size):
        """
        set icon size

        Parameters
        ----------
        size: QtCore.QSize
            size of the icon
        """
        self._size = size
        self.update()

    def update(self, *args, **kwargs):
        """Update label."""
        if self._icon:
            self.setPixmap(self._icon.pixmap(self._size))
        return super().update(*args, **kwargs)
